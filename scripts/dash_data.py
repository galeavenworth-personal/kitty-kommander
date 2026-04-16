"""Pure data layer for the cockpit dashboard.

All functions in this module are either pure (no I/O) or isolated data
fetchers.  The rendering layer (cockpit_dash.py) imports these — it never
calls subprocess or reads files directly.
"""

import json
import os
import subprocess
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
SPRITE_DIR = REPO_DIR / "sprites" / "nodes"
KITTY_SPRITE_DIR = REPO_DIR / "sprites" / "kitties"

PROJECT_DIR = os.environ.get("KITTY_KOMMANDER_DIR", os.getcwd())

# ── Tokyo Night Palette ──────────────────────────────────────────────────────

PAL = {
    "bg": "#1a1b26", "fg": "#a9b1d6", "accent": "#7aa2f7",
    "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68",
    "grey": "#565f89", "dark": "#24283b",
}

# Role accent colors (match MANIFEST.md)
ROLE_COLORS = {
    "kommander": "#a9b1d6",
    "lead": "#e0af68",
    "builder": "#ff9e64",
    "scout": "#7dcfff",
    "critic": "#bb9af7",
    "integrator": "#9ece6a",
}


# ── Data Fetchers (side-effectful but isolated) ─────────────────────────────

def bd(args, project_dir=None):
    """Run bd with --format=json and return parsed output."""
    cwd = project_dir or PROJECT_DIR
    try:
        result = subprocess.run(
            ["bd"] + args + ["--format=json"],
            capture_output=True, text=True, timeout=15, cwd=cwd,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return [] if args and args[0] in ("ready", "blocked", "list", "children") else {}


def git_log(n=10, project_dir=None):
    """Return list of oneline commit strings."""
    cwd = project_dir or PROJECT_DIR
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", f"-{n}"],
            capture_output=True, text=True, timeout=5, cwd=cwd,
        )
        return [line for line in r.stdout.strip().split("\n") if line]
    except Exception:
        return []


def get_mutations(limit=8, project_dir=None):
    """Read recent state mutations from the beads audit trail.

    Returns a list of dicts, most recent first:
        [{"timestamp": str, "issue_id": str, "short_id": str,
          "old_state": str, "new_state": str, "actor": str}, ...]
    """
    cwd = project_dir or PROJECT_DIR
    interactions_path = Path(cwd) / ".beads" / "interactions.jsonl"
    if not interactions_path.exists():
        return []

    mutations = []
    try:
        lines = interactions_path.read_text().strip().split("\n")
        for line in reversed(lines):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("kind") != "field_change":
                continue
            extra = entry.get("extra", {})
            if extra.get("field") != "status":
                continue
            issue_id = entry.get("issue_id", "")
            short_id = issue_id.split("-")[-1] if "-" in issue_id else issue_id
            mutations.append({
                "timestamp": entry.get("created_at", "")[:19].replace("T", " "),
                "issue_id": issue_id,
                "short_id": short_id,
                "old_state": extra.get("old_value", "?"),
                "new_state": extra.get("new_value", "?"),
                "actor": entry.get("actor", "unknown"),
            })
            if len(mutations) >= limit:
                break
    except Exception:
        pass
    return mutations


def get_agents(project_dir=None):
    """Return a list of active agents with their bead assignments.

    Returns a list of dicts:
        [{"name": str, "role": str, "color": str,
          "bead_id": str, "bead_title": str}, ...]
    """
    cwd = project_dir or PROJECT_DIR
    wip = bd(["list", "--status=in_progress", "-n", "100"], project_dir=cwd)
    agents = {}
    for issue in wip:
        assignee = issue.get("assignee", "") or issue.get("claimed_by", "")
        if not assignee:
            continue
        name = assignee.split("@")[0]  # Strip email domain if present
        sid = issue["id"].split("-")[-1] if "-" in issue["id"] else issue["id"]
        title = issue.get("title", "")[:36]
        # Infer role from agent name (convention: name contains role)
        role = _infer_role(name)
        if name not in agents:
            agents[name] = {
                "name": name,
                "role": role,
                "color": ROLE_COLORS.get(role, PAL["fg"]),
                "beads": [],
            }
        agents[name]["beads"].append({"id": sid, "title": title})
    return list(agents.values())


def _infer_role(name):
    """Infer agent role from name convention."""
    name_lower = name.lower()
    for role in ROLE_COLORS:
        if role in name_lower:
            return role
    return "builder"  # Default role


# ── Sprite Support ───────────────────────────────────────────────────────────

def sprite_path(state):
    """Return absolute path to yarn ball sprite for a state, or None."""
    p = SPRITE_DIR / f"yarn_{state}.png"
    return str(p) if p.exists() else None


def has_sprites():
    """Check if yarn ball sprites are available."""
    return all(
        (SPRITE_DIR / f"yarn_{s}.png").exists()
        for s in ("ready", "blocked", "wip", "open")
    )


def kitty_sprite_path(role, state, size="badge"):
    """Return absolute path to kitty sprite, or None if not found.

    Tries exact match first, then falls back to idle state.
    """
    p = KITTY_SPRITE_DIR / size / f"{role}_{state}.png"
    if p.exists():
        return str(p)
    # Fallback: idle pose for the role
    fallback = KITTY_SPRITE_DIR / size / f"{role}_idle.png"
    if fallback.exists():
        return str(fallback)
    return None


def has_kitty_sprites(size="badge"):
    """Check if any kitty badge sprites exist."""
    d = KITTY_SPRITE_DIR / size
    return d.is_dir() and any(d.glob("*.png"))


# ── Pure Functions (no I/O) ──────────────────────────────────────────────────

def build_dag_dot(blocked, ready, all_open, wip, assignee_map=None):
    """Generate Graphviz DOT string from beads issue data.

    Pure function — no I/O, no subprocess calls.

    Parameters
    ----------
    blocked : list[dict]
        Issues from bd blocked (each has 'id', 'title', 'blocked_by').
    ready : list[dict]
        Issues from bd ready (each has 'id').
    all_open : list[dict]
        Issues from bd list --status=open (each has 'id', 'title').
    wip : list[dict]
        Issues from bd list --status=in_progress (each has 'id').
    assignee_map : dict[str, str] | None
        Optional mapping of issue_id → agent_name for kitty badge overlay.

    Returns
    -------
    str or None
        DOT string for graphviz, or None if no dependency chains exist.
    """
    if assignee_map is None:
        assignee_map = {}

    ready_ids = {r["id"] for r in ready}
    wip_ids = {r["id"] for r in wip}
    title_map = {i["id"]: i.get("title", "") for i in all_open + wip}
    blocked_ids = {b["id"] for b in blocked}

    # Build nodes + edges from blocked dependency data
    nodes = {}  # id → {"label": str, "state": str}
    edges = []  # [(src, dst)]

    for issue in blocked:
        sid = issue["id"].split("-")[-1]
        title = issue.get("title", "")[:32]
        nodes[issue["id"]] = {"label": f"{sid}: {title}", "state": "blocked"}

        for blocker_id in issue.get("blocked_by", []):
            edges.append((blocker_id, issue["id"]))
            if blocker_id not in nodes:
                b_sid = blocker_id.split("-")[-1]
                b_title = title_map.get(blocker_id, "")[:32]
                if blocker_id in wip_ids:
                    state = "wip"
                elif blocker_id in ready_ids:
                    state = "ready"
                elif blocker_id in blocked_ids:
                    state = "blocked"
                else:
                    state = "open"
                nodes[blocker_id] = {"label": f"{b_sid}: {b_title}", "state": state}

    if not nodes:
        return None

    use_sprites = has_sprites()
    use_kitty = has_kitty_sprites()

    # Generate DOT
    fill_map = {
        "blocked": PAL["red"], "ready": PAL["green"],
        "wip": PAL["yellow"], "open": PAL["grey"],
    }

    # Edge color: yarn strand in accent blue, fading to dark
    edge_color = f"{PAL['accent']}:{PAL['dark']}"

    dot = [
        "digraph G {",
        f'  graph [bgcolor="{PAL["bg"]}", pad="0.8", nodesep="1.0",'
        f' ranksep="1.8", fontname="Noto Sans Mono", rankdir="TB",'
        f' splines="curved"];',
    ]

    if use_sprites:
        # Image-based yarn ball nodes
        dot.append(
            f'  node [shape="none", fontname="Noto Sans Mono",'
            f' fontsize="9", fontcolor="{PAL["fg"]}", labelloc="b",'
            f' imagepos="tc", imagescale="true", fixedsize="true",'
            f' width="1.0", height="1.3"];'
        )
    else:
        # Fallback: styled circles (yarn ball aesthetic without sprites)
        dot.append(
            f'  node [shape="circle", style="filled", fontname="Noto Sans Mono",'
            f' fontsize="9", penwidth="2.0", fixedsize="true",'
            f' width="0.9", height="0.9"];'
        )

    dot.append(
        f'  edge [color="{edge_color}", penwidth="2.5",'
        f' arrowsize="0.6", arrowhead="vee"];'
    )

    for nid, node in nodes.items():
        fill = fill_map.get(node["state"], PAL["grey"])
        fc = PAL["bg"] if node["state"] in ("ready", "blocked", "wip") else PAL["fg"]
        label = node["label"].replace('"', '\\"')

        sp = sprite_path(node["state"]) if use_sprites else None

        # Check for kitty badge overlay
        agent_name = assignee_map.get(nid, "")
        role = _infer_role(agent_name) if agent_name else ""
        ksp = kitty_sprite_path(role, node["state"]) if (use_kitty and agent_name) else None

        if sp:
            # Yarn ball sprite node
            extra = ""
            if node["state"] == "wip":
                extra = f', penwidth="3.0", color="{PAL["fg"]}"'
            if ksp:
                # Composite: yarn ball + kitty badge as xlabel
                dot.append(
                    f'  "{nid}" [image="{sp}", label="{label}",'
                    f' xlabel=<<TABLE BORDER="0"><TR><TD><IMG SRC="{ksp}"/></TD></TR></TABLE>>{extra}];'
                )
            else:
                dot.append(
                    f'  "{nid}" [image="{sp}", label="{label}"{extra}];'
                )
        else:
            # Fallback styled circle
            if node["state"] == "wip":
                dot.append(
                    f'  "{nid}" [label="{label}", fillcolor="{fill}",'
                    f' fontcolor="{fc}", penwidth="4.0",'
                    f' style="filled,dashed", color="{PAL["fg"]}"];'
                )
            else:
                dot.append(
                    f'  "{nid}" [label="{label}", fillcolor="{fill}",'
                    f' fontcolor="{fc}"];'
                )

    for src, dst in edges:
        dot.append(f'  "{src}" -> "{dst}";')

    dot.append("}")
    return "\n".join(dot)


def build_sidebar_text(stats, ready, commits, mutations=None, agents=None,
                       bar_width=50):
    """Generate the complete sidebar text as a string.

    Pure function — no I/O, no subprocess calls.

    Parameters
    ----------
    stats : dict
        Output from bd stats (has 'summary' key).
    ready : list[dict]
        Issues from bd ready.
    commits : list[str]
        Oneline git log strings.
    mutations : list[dict] | None
        Recent state mutations from get_mutations().
    agents : list[dict] | None
        Active agents from get_agents().
    bar_width : int
        Width for the progress bar.

    Returns
    -------
    str
        Complete sidebar text with ANSI color codes.
    """
    if mutations is None:
        mutations = []
    if agents is None:
        agents = []

    summary = stats.get("summary", {}) if isinstance(stats, dict) else {}
    total = summary.get("total_issues", 0)
    closed = summary.get("closed_issues", 0)
    open_n = summary.get("open_issues", 0)
    blocked_n = summary.get("blocked_issues", 0)
    ready_n = summary.get("ready_issues", 0)
    wip_n = summary.get("in_progress_issues", 0)

    lines = []

    # ANSI helpers (inline to keep pure)
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

    # ── Health ──
    pct = int((closed / total) * 100) if total > 0 else 0
    lines.append(f"\n  {BOLD}{C_FG}PROJECT HEALTH{RST}  {C_ACCENT}{pct}%{RST} complete")
    lines.append("")

    if total > 0:
        c = max(int((closed / total) * bar_width), 0)
        r = max(int((ready_n / total) * bar_width), 0)
        b = max(int((blocked_n / total) * bar_width), 0)
        o = max(bar_width - c - r - b, 0)
        bar = f"{C_GREY}{'█' * c}{C_GREEN}{'█' * r}{C_RED}{'█' * b}{C_FG}{'░' * o}"
        lines.append(f"  {bar}{RST}")
        lines.append("")

    legend = (
        f"  {C_GREY}■ {closed} closed  "
        f"{C_GREEN}■ {ready_n} ready  "
        f"{C_RED}■ {blocked_n} blocked  "
        f"{C_YELLOW}■ {wip_n} wip  "
        f"{C_FG}■ {open_n} open{RST}"
    )
    lines.append(legend)
    lines.append(f"\n  {C_GREY}{'─' * bar_width}{RST}")

    # ── Ready Queue ──
    lines.append(f"\n  {BOLD}{C_GREEN}READY QUEUE{RST}")
    lines.append("")

    for issue in ready[:12]:
        pri = issue.get("priority", 4)
        pri_c = C_RED if pri <= 1 else (C_YELLOW if pri == 2 else C_GREY)
        sid = issue["id"].split("-")[-1]
        title = issue.get("title", "")[:42]
        lines.append(f"  {C_GREY}{sid}{RST}  {pri_c}P{pri}{RST}  {C_FG}{title}{RST}")

    if len(ready) > 12:
        lines.append(f"  {C_GREY}... +{len(ready) - 12} more{RST}")

    lines.append(f"\n  {C_GREY}{'─' * bar_width}{RST}")

    # ── Recent Mutations ──
    lines.append(f"\n  {BOLD}{C_YELLOW}RECENT MUTATIONS{RST}")
    lines.append("")

    if mutations:
        for m in mutations[:8]:
            ts = m["timestamp"].split(" ")[-1] if " " in m["timestamp"] else m["timestamp"]
            old_c = _state_color(m["old_state"], C_RED, C_GREEN, C_YELLOW, C_GREY, C_FG)
            new_c = _state_color(m["new_state"], C_RED, C_GREEN, C_YELLOW, C_GREY, C_FG)
            lines.append(
                f"  {C_GREY}{ts}{RST}  {C_ACCENT}{m['short_id']}{RST}  "
                f"{old_c}{m['old_state']}{RST} → {new_c}{m['new_state']}{RST}  "
                f"{DIM}{m['actor']}{RST}"
            )
    else:
        lines.append(f"  {C_GREY}(no recent mutations){RST}")

    lines.append(f"\n  {C_GREY}{'─' * bar_width}{RST}")

    # ── Agents ──
    lines.append(f"\n  {BOLD}{C_ACCENT}AGENTS{RST}")
    lines.append("")

    if agents:
        for agent in agents:
            role_c = _ansi(agent.get("color", PAL["fg"]))
            lines.append(
                f"  {role_c}█{RST} {C_FG}{agent['name']}{RST}  "
                f"{DIM}{agent['role']}{RST}"
            )
            for bead in agent.get("beads", [])[:3]:
                lines.append(
                    f"    {C_GREY}↳ {bead['id']}{RST}  {C_FG}{bead['title']}{RST}"
                )
    else:
        lines.append(f"  {C_GREY}(no active agents){RST}")

    lines.append(f"\n  {C_GREY}{'─' * bar_width}{RST}")

    # ── Recent Commits ──
    lines.append(f"\n  {BOLD}{C_ACCENT}RECENT COMMITS{RST}")
    lines.append("")

    for commit in commits[:8]:
        parts = commit.split(" ", 1)
        sha = parts[0] if parts else ""
        msg = parts[1][:48] if len(parts) > 1 else ""
        lines.append(f"  {C_YELLOW}{sha}{RST}  {C_FG}{msg}{RST}")

    if not commits:
        lines.append(f"  {C_GREY}(no commits){RST}")

    return "\n".join(lines)


def _state_color(state, c_red, c_green, c_yellow, c_grey, c_fg):
    """Return ANSI color for a bead state."""
    return {
        "blocked": c_red,
        "closed": c_green,
        "in_progress": c_yellow,
        "open": c_grey,
    }.get(state, c_fg)
