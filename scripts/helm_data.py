"""Helm data layer — cell-level topology and status for multi-cell view.

All functions in this module are either pure (no I/O) or isolated data
fetchers.  The rendering layer (cockpit_dash.py) imports these — it never
calls subprocess or reads files directly.

Covers beads tracks wvf.1 (topology) and wvf.2 (status).
"""

import json
import os
import subprocess
import time
from pathlib import Path

from dash_data import PAL, ROLE_COLORS, _infer_role

# ── Paths ────────────────────────────────────────────────────────────────────

PROJECT_DIR = os.environ.get("KITTY_KOMMANDER_DIR", os.getcwd())


# ── Data Fetchers (side-effectful but isolated) ─────────────────────────────

def _bd_raw(args, project_dir=None):
    """Run bd with given args and return parsed JSON output."""
    cwd = project_dir or PROJECT_DIR
    try:
        result = subprocess.run(
            ["bd"] + args + ["--format=json"],
            capture_output=True, text=True, timeout=15, cwd=cwd,
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            return data
    except (subprocess.TimeoutExpired, json.JSONDecodeError,
            FileNotFoundError, OSError):
        pass
    return None


def get_cell_topology(project_dir=None):
    """Fetch cell topology from federation peers and per-cell stats.

    Returns
    -------
    list[dict]
        Each cell dict has: name, project_dir, url, stats (dict with
        total/closed/open/blocked/wip/ready counts), has_sub_cells (bool),
        sync_age_seconds (int), sync_status ("healthy"|"stale"|"unknown"),
        gates (list of gate dicts), parent (str|None).
    """
    cwd = project_dir or PROJECT_DIR

    # Get federation peers
    peers_data = _bd_raw(["federation", "list-peers"], project_dir=cwd)
    if not peers_data:
        return []

    # Normalize: handle both list and dict-with-list responses
    if isinstance(peers_data, dict):
        peers = peers_data.get("peers", peers_data.get("cells", []))
    elif isinstance(peers_data, list):
        peers = peers_data
    else:
        return []

    cells = []
    for peer in peers:
        name = peer.get("name", "unknown")
        peer_dir = peer.get("project_dir", peer.get("path", ""))
        url = peer.get("url", peer.get("remote", ""))
        parent = peer.get("parent", None)

        # Get per-cell stats
        stats_data = _bd_raw(["stats"], project_dir=peer_dir) if peer_dir else None
        summary = {}
        if isinstance(stats_data, dict):
            summary = stats_data.get("summary", stats_data)

        stats = {
            "total": summary.get("total_issues", 0),
            "closed": summary.get("closed_issues", 0),
            "open": summary.get("open_issues", 0),
            "blocked": summary.get("blocked_issues", 0),
            "wip": summary.get("in_progress_issues", 0),
            "ready": summary.get("ready_issues", 0),
        }

        # Determine sub-cell status
        has_sub_cells = bool(peer.get("has_sub_cells", peer.get("children", [])))

        # Sync age
        last_sync = peer.get("last_sync", peer.get("synced_at", ""))
        sync_age = _compute_sync_age(last_sync)
        if sync_age < 0:
            sync_status = "unknown"
        elif sync_age > 300:
            sync_status = "stale"
        else:
            sync_status = "healthy"

        # Gates for this cell
        gates_data = _bd_raw(["gate", "check"], project_dir=peer_dir) if peer_dir else None
        gates = _normalize_gates(gates_data)

        cells.append({
            "name": name,
            "project_dir": peer_dir,
            "url": url,
            "stats": stats,
            "has_sub_cells": has_sub_cells,
            "sync_age_seconds": max(sync_age, 0),
            "sync_status": sync_status,
            "gates": gates,
            "parent": parent,
        })

    return cells


def get_cell_status(project_dir=None):
    """Fetch cell status including lead, agents, progress, and gates.

    Returns
    -------
    list[dict]
        Each has: name, lead (str), agents (list of agent dicts),
        progress ({done, total, pct}), gates (list of gate dicts),
        group_type (str).
    """
    cells = get_cell_topology(project_dir=project_dir)
    statuses = []

    for cell in cells:
        stats = cell.get("stats", {})
        total = stats.get("total", 0)
        done = stats.get("closed", 0)
        pct = int((done / total) * 100) if total > 0 else 0

        # Get agents for this cell
        agents = _get_cell_agents(cell.get("project_dir"))

        # Determine lead
        lead = ""
        for agent in agents:
            if agent.get("role") == "lead":
                lead = agent.get("name", "")
                break
        if not lead and agents:
            lead = agents[0].get("name", "unknown")

        gt = group_type(stats, cell.get("has_sub_cells", False))

        statuses.append({
            "name": cell["name"],
            "lead": lead,
            "agents": agents,
            "progress": {"done": done, "total": total, "pct": pct},
            "gates": cell.get("gates", []),
            "group_type": gt,
        })

    return statuses


def get_cross_cell_gates(project_dir=None):
    """Fetch cross-cell gate status.

    Returns
    -------
    list[dict]
        Each has: gate_id, source_cell, source_bead, status
        ("resolved"|"pending"), resolved_at (str|None).
    """
    cwd = project_dir or PROJECT_DIR
    data = _bd_raw(["gate", "check"], project_dir=cwd)
    return _normalize_gates(data)


def get_cell_mutations(limit=8, project_dir=None):
    """Read recent inter-cell mutations (sync, completion, gate resolution).

    Returns
    -------
    list[dict]
        Each has: timestamp, event, cell, detail.
    """
    cwd = project_dir or PROJECT_DIR
    interactions_path = Path(cwd) / ".beads" / "interactions.jsonl"
    if not interactions_path.exists():
        return []

    mutations = []
    try:
        lines = interactions_path.read_text().strip().split("\n")
        cell_events = {"federation_sync", "cell_deploy", "cell_teardown",
                       "gate_resolved", "gate_created", "mol_closed"}
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = entry.get("kind", "")
            # Include cell-level events + status changes on federation items
            if kind in cell_events:
                mutations.append({
                    "timestamp": entry.get("created_at", "")[:19].replace("T", " "),
                    "event": kind,
                    "cell": entry.get("cell", entry.get("actor", "unknown")),
                    "detail": entry.get("extra", {}).get("summary",
                              entry.get("extra", {}).get("detail", kind)),
                })
            elif kind == "field_change":
                extra = entry.get("extra", {})
                if extra.get("field") == "status" and extra.get("scope") == "cell":
                    issue_id = entry.get("issue_id", "")
                    short_id = issue_id.split("-")[-1] if "-" in issue_id else issue_id
                    mutations.append({
                        "timestamp": entry.get("created_at", "")[:19].replace("T", " "),
                        "event": f"{extra.get('old_value', '?')} -> {extra.get('new_value', '?')}",
                        "cell": entry.get("actor", "unknown"),
                        "detail": short_id,
                    })
            if len(mutations) >= limit:
                break
    except Exception:
        pass
    return mutations


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _compute_sync_age(last_sync_str):
    """Return seconds since last sync, or -1 if unparseable."""
    if not last_sync_str:
        return -1
    try:
        from datetime import datetime
        # Handle ISO format with or without timezone
        clean = last_sync_str.replace("Z", "+00:00")
        if "+" not in clean and "T" in clean:
            dt = datetime.fromisoformat(clean)
        else:
            dt = datetime.fromisoformat(clean)
        now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
        return int((now - dt).total_seconds())
    except (ValueError, TypeError):
        return -1


def _normalize_gates(data):
    """Normalize gate data from bd gate check into a list of gate dicts."""
    if not data:
        return []
    if isinstance(data, dict):
        gates = data.get("gates", data.get("items", []))
    elif isinstance(data, list):
        gates = data
    else:
        return []

    result = []
    for g in gates:
        result.append({
            "gate_id": g.get("gate_id", g.get("id", "")),
            "source_cell": g.get("source_cell", g.get("cell", "")),
            "source_bead": g.get("source_bead", g.get("bead", "")),
            "status": g.get("status", "pending"),
            "resolved_at": g.get("resolved_at", None),
        })
    return result


def _get_cell_agents(cell_dir):
    """Get agents working in a specific cell directory."""
    if not cell_dir:
        return []
    wip = _bd_raw(["list", "--status=in_progress", "-n", "100"], project_dir=cell_dir)
    if not wip or not isinstance(wip, list):
        return []

    agents = {}
    for issue in wip:
        assignee = issue.get("assignee", "") or issue.get("claimed_by", "")
        if not assignee:
            continue
        name = assignee.split("@")[0]
        role = _infer_role(name)
        status = issue.get("status", "in_progress")
        bead_id = issue.get("id", "")
        short_id = bead_id.split("-")[-1] if "-" in bead_id else bead_id

        if name not in agents:
            agents[name] = {
                "name": name,
                "role": role,
                "color": ROLE_COLORS.get(role, PAL["fg"]),
                "status": status,
                "current_bead": short_id,
            }
    return list(agents.values())


# ── Pure Functions (no I/O) ─────────────────────────────────────────────────

def group_type(cell_stats, has_sub_cells):
    """Determine the group type label for a cell.

    Parameters
    ----------
    cell_stats : dict
        Stats dict with total, closed, open, blocked, wip, ready counts.
    has_sub_cells : bool
        Whether this cell has deployed sub-cells.

    Returns
    -------
    str
        One of "Clowder", "Nuisance", "Glaring", "Pounce".
    """
    if has_sub_cells:
        return "Clowder"

    blocked = cell_stats.get("blocked", 0)
    total = cell_stats.get("total", 0)

    # Check for failed/blocked conditions
    # "failed" is indicated by high blocked count
    if blocked > 0 and total > 0 and blocked > total * 0.5:
        return "Glaring"

    # Any blocked items = nuisance
    if blocked > 0:
        return "Nuisance"

    return "Pounce"


def build_helm_dot(cells, edges=None):
    """Generate Graphviz DOT string for cell-level DAG.

    Parameters
    ----------
    cells : list[dict]
        Cell dicts from get_cell_topology(). Each has: name, stats,
        has_sub_cells, sync_status, gates, parent.
    edges : list[tuple] | None
        Optional extra edges as (source_name, target_name) tuples.
        Parent-child edges are derived automatically from cell['parent'].

    Returns
    -------
    str or None
        DOT string for graphviz, or None if no cells exist.
    """
    if not cells:
        return None

    # Border color by status
    def _border_color(cell):
        stats = cell.get("stats", {})
        blocked = stats.get("blocked", 0)
        wip = stats.get("wip", 0)
        total = stats.get("total", 0)
        closed = stats.get("closed", 0)
        if blocked > 0:
            return PAL["red"]
        if total > 0 and closed == total:
            return PAL["green"]
        if wip > 0:
            return PAL["yellow"]
        return PAL["green"]

    # Health summary text
    def _health_text(stats):
        total = stats.get("total", 0)
        closed = stats.get("closed", 0)
        if total == 0:
            return "No beads"
        if closed == total:
            return f"■ {closed}/{total} COMPLETE"
        pct = int((closed / total) * 100)
        filled = max(int(pct / 10), 0)
        empty = 10 - filled
        return f"{'▸' * filled}{'·' * empty} {pct}%"

    # Gate blocker text
    def _gate_text(gates):
        pending = [g for g in gates if g.get("status") == "pending"]
        if not pending:
            return ""
        return f"⚠ {len(pending)} gate{'s' if len(pending) != 1 else ''} pending"

    dot = [
        "digraph Helm {",
        f'  graph [bgcolor="{PAL["bg"]}", pad="0.8", nodesep="1.2",'
        f' ranksep="1.5", fontname="Noto Sans Mono", rankdir="TB",'
        f' splines="curved"];',
        f'  node [shape="box", style="filled,rounded", fontname="Noto Sans Mono",'
        f' fontsize="10", fillcolor="{PAL["dark"]}"];',
        f'  edge [color="{PAL["accent"]}:{PAL["dark"]}", penwidth="2.0",'
        f' arrowsize="0.7", arrowhead="vee"];',
    ]

    for cell in cells:
        name = cell.get("name", "unknown")
        safe_name = name.replace('"', '\\"')
        stats = cell.get("stats", {})
        gt = group_type(stats, cell.get("has_sub_cells", False))
        health = _health_text(stats)
        border = _border_color(cell)
        gate_info = _gate_text(cell.get("gates", []))

        # Build HTML-like label
        label_parts = [
            f'<B>{safe_name}</B>',
            f'<I>{gt}</I>',
            health,
        ]
        if gate_info:
            label_parts.append(f'<FONT COLOR="{PAL["red"]}">{gate_info}</FONT>')

        label = "<BR/>".join(label_parts)

        dot.append(
            f'  "{safe_name}" [label=<{label}>,'
            f' color="{border}", fontcolor="{PAL["fg"]}"];'
        )

    # Build edges from parent fields
    all_edges = []
    for cell in cells:
        parent = cell.get("parent")
        if parent:
            all_edges.append((parent, cell["name"]))

    if edges:
        all_edges.extend(edges)

    for src, dst in all_edges:
        safe_src = src.replace('"', '\\"')
        safe_dst = dst.replace('"', '\\"')
        dot.append(f'  "{safe_src}" -> "{safe_dst}";')

    dot.append("}")
    return "\n".join(dot)


def build_helm_status_text(cells, gates, mutations, bar_width=50):
    """Generate ANSI-colored text for the Cell Status pane.

    Parameters
    ----------
    cells : list[dict]
        Cell status dicts from get_cell_status(). Each has: name, lead,
        agents, progress, gates, group_type.
    gates : list[dict]
        Cross-cell gate dicts from get_cross_cell_gates().
    mutations : list[dict]
        Inter-cell mutation dicts from get_cell_mutations().
    bar_width : int
        Width for progress bars.

    Returns
    -------
    str
        Complete status text with ANSI color codes.
    """
    lines = []

    # ANSI helpers
    def _ansi(hex_color):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return f"\033[38;2;{r};{g};{b}m"

    RST = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    C_RED = _ansi(PAL["red"])
    C_GREEN = _ansi(PAL["green"])
    C_YELLOW = _ansi(PAL["yellow"])
    C_GREY = _ansi(PAL["grey"])
    C_ACCENT = _ansi(PAL["accent"])
    C_FG = _ansi(PAL["fg"])

    # ── Cell Status Cards ──
    lines.append(f"\n  {BOLD}{C_FG}CELL STATUS{RST}")
    lines.append("")

    if cells:
        for cell in cells:
            name = cell.get("name", "unknown")
            lead = cell.get("lead", "")
            gt = cell.get("group_type", "Pounce")
            progress = cell.get("progress", {})
            done = progress.get("done", 0)
            total = progress.get("total", 0)
            pct = progress.get("pct", 0)

            # Cell header
            gt_color = {
                "Clowder": C_ACCENT, "Nuisance": C_RED,
                "Glaring": C_YELLOW, "Pounce": C_GREEN,
            }.get(gt, C_FG)
            lines.append(
                f"  {BOLD}{C_FG}{name}{RST}  "
                f"{gt_color}{gt}{RST}  "
                f"{DIM}lead: {lead}{RST}"
            )

            # Progress bar
            if total > 0:
                filled = max(int((pct / 100) * bar_width), 0)
                empty = bar_width - filled
                bar_color = C_GREEN if pct >= 80 else (C_YELLOW if pct >= 40 else C_RED)
                lines.append(
                    f"  {bar_color}{'█' * filled}{C_GREY}{'░' * empty}{RST}"
                    f"  {C_FG}{done}/{total}{RST} ({pct}%)"
                )
            else:
                lines.append(f"  {C_GREY}(no beads){RST}")

            # Agent roster
            agents = cell.get("agents", [])
            if agents:
                for agent in agents:
                    role_c = _ansi(agent.get("color", PAL["fg"]))
                    lines.append(
                        f"    {role_c}█{RST} {C_FG}{agent['name']}{RST}  "
                        f"{DIM}{agent['role']}{RST}  "
                        f"{C_GREY}→ {agent.get('current_bead', '')}{RST}"
                    )

            # Cell gates
            cell_gates = cell.get("gates", [])
            pending_gates = [g for g in cell_gates if g.get("status") == "pending"]
            if pending_gates:
                lines.append(
                    f"    {C_RED}⚠ {len(pending_gates)} pending gate"
                    f"{'s' if len(pending_gates) != 1 else ''}{RST}"
                )

            lines.append("")

    else:
        lines.append(f"  {C_GREY}(no cells){RST}")

    lines.append(f"  {C_GREY}{'─' * bar_width}{RST}")

    # ── Cross-Cell Gates ──
    lines.append(f"\n  {BOLD}{C_YELLOW}CROSS-CELL GATES{RST}")
    lines.append("")

    if gates:
        for g in gates:
            status = g.get("status", "pending")
            status_c = C_GREEN if status == "resolved" else C_RED
            status_icon = "✓" if status == "resolved" else "⏳"
            resolved = g.get("resolved_at", "")
            resolved_text = f"  {DIM}{resolved[:19]}{RST}" if resolved else ""
            lines.append(
                f"  {status_c}{status_icon}{RST}  "
                f"{C_ACCENT}{g.get('gate_id', '')}{RST}  "
                f"{C_FG}{g.get('source_cell', '')}{RST} → "
                f"{C_GREY}{g.get('source_bead', '')}{RST}"
                f"{resolved_text}"
            )
    else:
        lines.append(f"  {C_GREY}(no cross-cell gates){RST}")

    lines.append(f"\n  {C_GREY}{'─' * bar_width}{RST}")

    # ── Mutations ──
    lines.append(f"\n  {BOLD}{C_YELLOW}MUTATIONS{RST}")
    lines.append("")

    if mutations:
        for m in mutations[:8]:
            ts = m.get("timestamp", "")
            ts_short = ts.split(" ")[-1] if " " in ts else ts
            lines.append(
                f"  {C_GREY}{ts_short}{RST}  "
                f"{C_ACCENT}{m.get('cell', '')}{RST}  "
                f"{C_FG}{m.get('event', '')}{RST}  "
                f"{DIM}{m.get('detail', '')}{RST}"
            )
    else:
        lines.append(f"  {C_GREY}(no recent cell mutations){RST}")

    return "\n".join(lines)


def build_federation_footer(cells):
    """Generate ANSI string showing federation sync status per peer.

    Parameters
    ----------
    cells : list[dict]
        Cell dicts from get_cell_topology().

    Returns
    -------
    str
        ANSI-colored footer text showing sync health per cell.
    """
    if not cells:
        return ""

    def _ansi(hex_color):
        r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
        return f"\033[38;2;{r};{g};{b}m"

    RST = "\033[0m"
    DIM = "\033[2m"
    C_GREEN = _ansi(PAL["green"])
    C_YELLOW = _ansi(PAL["yellow"])
    C_RED = _ansi(PAL["red"])
    C_GREY = _ansi(PAL["grey"])
    C_FG = _ansi(PAL["fg"])

    lines = [f"\n  {DIM}{C_GREY}Federation Sync{RST}"]

    for cell in cells:
        name = cell.get("name", "unknown")
        sync_status = cell.get("sync_status", "unknown")
        age = cell.get("sync_age_seconds", -1)

        if sync_status == "healthy":
            icon = f"{C_GREEN}●{RST}"
        elif sync_status == "stale":
            icon = f"{C_YELLOW}●{RST}"
        else:
            icon = f"{C_RED}●{RST}"

        if age >= 0:
            if age < 60:
                age_text = f"{age}s ago"
            elif age < 3600:
                age_text = f"{age // 60}m ago"
            else:
                age_text = f"{age // 3600}h ago"
        else:
            age_text = "unknown"

        lines.append(f"  {icon} {C_FG}{name}{RST}  {DIM}{age_text}{RST}")

    return "\n".join(lines)
