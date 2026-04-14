#!/usr/bin/env python3
"""Cockpit dashboard — beads DAG + project health for the Kitty terminal.

Usage:
    cockpit_dash.py --dag       # Left pane: dependency graph (graphviz → timg)
    cockpit_dash.py --sidebar   # Right pane: stats + ready queue + activity

Auto-refreshes every 30 seconds. Ctrl-C to exit.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

# --- Tokyo Night Palette ---
PAL = {
    "bg": "#1a1b26", "fg": "#a9b1d6", "accent": "#7aa2f7",
    "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68",
    "grey": "#565f89", "dark": "#24283b",
}

TIMG = "/usr/bin/timg"
PROJECT_DIR = os.environ.get(
    "KITTY_KOMMANDER_DIR",
    os.getcwd(),
)


def ansi(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"\033[38;2;{r};{g};{b}m"


RST = "\033[0m"
CLR = "\033[2J\033[H"
BOLD = "\033[1m"
DIM = "\033[2m"

C_RED = ansi(PAL["red"])
C_GREEN = ansi(PAL["green"])
C_YELLOW = ansi(PAL["yellow"])
C_GREY = ansi(PAL["grey"])
C_ACCENT = ansi(PAL["accent"])
C_FG = ansi(PAL["fg"])


# ── Data Layer ────────────────────────────────────────────────────────────────

def bd(args):
    """Run bd with --format=json and return parsed output."""
    try:
        result = subprocess.run(
            ["bd"] + args + ["--format=json"],
            capture_output=True, text=True, timeout=15, cwd=PROJECT_DIR,
        )
        if result.stdout.strip():
            return json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        pass
    return [] if args[0] in ("ready", "blocked", "list") else {}


def git_log(n=10):
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "--no-decorate", f"-{n}"],
            capture_output=True, text=True, timeout=5, cwd=PROJECT_DIR,
        )
        return [l for l in r.stdout.strip().split("\n") if l]
    except Exception:
        return []


def term_size():
    return shutil.get_terminal_size((120, 40))


# ── DAG Rendering ─────────────────────────────────────────────────────────────

def render_dag():
    blocked = bd(["blocked"])
    ready = bd(["ready", "-n", "100"])
    all_open = bd(["list", "--status=open", "-n", "100"])
    wip = bd(["list", "--status=in_progress", "-n", "100"])

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
        sys.stdout.write(CLR)
        print(f"\n  {C_GREEN}No dependency chains — all issues independent.{RST}")
        sys.stdout.flush()
        return

    # Generate DOT
    fill_map = {
        "blocked": PAL["red"], "ready": PAL["green"],
        "wip": PAL["yellow"], "open": PAL["grey"],
    }

    dot = [
        "digraph G {",
        f'  graph [bgcolor="{PAL["bg"]}", pad="1.0", nodesep="0.8",'
        f' ranksep="1.5", fontname="Noto Sans Mono", rankdir="TB"];',
        f'  node [shape="box", style="filled,rounded", fontname="Noto Sans Mono",'
        f' fontsize="10", penwidth="1.5", margin="0.3,0.2"];',
        f'  edge [color="{PAL["accent"]}", penwidth="1.5", arrowsize="0.8"];',
    ]

    for nid, node in nodes.items():
        fill = fill_map.get(node["state"], PAL["grey"])
        fc = PAL["bg"] if node["state"] in ("ready", "blocked", "wip") else PAL["fg"]
        label = node["label"].replace('"', '\\"')
        if node["state"] == "wip":
            dot.append(
                f'  "{nid}" [label="{label}", fillcolor="{fill}",'
                f' fontcolor="{fc}", penwidth="4.0",'
                f' style="filled,rounded,dashed", color="{PAL["fg"]}"];'
            )
        else:
            dot.append(f'  "{nid}" [label="{label}", fillcolor="{fill}", fontcolor="{fc}"];')

    for src, dst in edges:
        dot.append(f'  "{src}" -> "{dst}";')

    dot.append("}")
    dot_str = "\n".join(dot)

    # Render: dot → PNG pipe → timg
    cols, rows = term_size()
    gw = min(cols, 180)
    gh = min(rows - 2, 55)

    try:
        dot_proc = subprocess.Popen(
            ["dot", "-Tpng", "-Gdpi=150"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        png, _ = dot_proc.communicate(dot_str.encode(), timeout=10)

        if dot_proc.returncode != 0 or not png:
            sys.stdout.write(CLR)
            print(f"\n  {C_RED}graphviz error (exit {dot_proc.returncode}){RST}")
            sys.stdout.flush()
            return

        sys.stdout.write(CLR)
        sys.stdout.flush()

        timg_proc = subprocess.Popen(
            [TIMG, "--clear", "--center", "-g", f"{gw}x{gh}", "-p", "kitty", "-"],
            stdin=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        timg_proc.communicate(png, timeout=10)

    except Exception as e:
        sys.stdout.write(CLR)
        print(f"\n  {C_RED}Render error: {e}{RST}")
        sys.stdout.flush()


# ── Sidebar Rendering ─────────────────────────────────────────────────────────

def render_sidebar():
    stats_raw = bd(["stats"])
    stats = stats_raw.get("summary", {})
    ready = bd(["ready", "-n", "100"])
    commits = git_log(10)

    total = stats.get("total_issues", 0)
    closed = stats.get("closed_issues", 0)
    open_n = stats.get("open_issues", 0)
    blocked_n = stats.get("blocked_issues", 0)
    ready_n = stats.get("ready_issues", 0)
    wip_n = stats.get("in_progress_issues", 0)

    cols, _ = term_size()
    bar_w = min(cols - 6, 50)

    sys.stdout.write(CLR)

    # ── Health ──
    pct = int((closed / total) * 100) if total > 0 else 0
    print(f"\n  {BOLD}{C_FG}PROJECT HEALTH{RST}  {C_ACCENT}{pct}%{RST} complete")
    print()

    if total > 0:
        c = max(int((closed / total) * bar_w), 0)
        r = max(int((ready_n / total) * bar_w), 0)
        b = max(int((blocked_n / total) * bar_w), 0)
        o = max(bar_w - c - r - b, 0)
        bar = f"{C_GREY}{'█' * c}{C_GREEN}{'█' * r}{C_RED}{'█' * b}{C_FG}{'░' * o}"
        print(f"  {bar}{RST}")
        print()

    legend = (
        f"  {C_GREY}■ {closed} closed  "
        f"{C_GREEN}■ {ready_n} ready  "
        f"{C_RED}■ {blocked_n} blocked  "
        f"{C_YELLOW}■ {wip_n} wip  "
        f"{C_FG}■ {open_n} open{RST}"
    )
    print(legend)
    print(f"\n  {C_GREY}{'─' * bar_w}{RST}")

    # ── Ready Queue ──
    print(f"\n  {BOLD}{C_GREEN}READY QUEUE{RST}")
    print()

    for issue in ready[:12]:
        pri = issue.get("priority", 4)
        pri_c = C_RED if pri <= 1 else (C_YELLOW if pri == 2 else C_GREY)
        sid = issue["id"].split("-")[-1]
        title = issue.get("title", "")[:42]
        print(f"  {C_GREY}{sid}{RST}  {pri_c}P{pri}{RST}  {C_FG}{title}{RST}")

    if len(ready) > 12:
        print(f"  {C_GREY}... +{len(ready) - 12} more{RST}")

    print(f"\n  {C_GREY}{'─' * bar_w}{RST}")

    # ── Recent Commits ──
    print(f"\n  {BOLD}{C_ACCENT}RECENT COMMITS{RST}")
    print()

    for commit in commits[:8]:
        parts = commit.split(" ", 1)
        sha = parts[0] if parts else ""
        msg = parts[1][:48] if len(parts) > 1 else ""
        print(f"  {C_YELLOW}{sha}{RST}  {C_FG}{msg}{RST}")

    if not commits:
        print(f"  {C_GREY}(no commits){RST}")

    # ── Timestamp ──
    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n  {DIM}{C_GREY}Updated {now}  •  30s refresh{RST}")
    sys.stdout.flush()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("--dag", "--sidebar"):
        print("Usage: cockpit_dash.py [--dag | --sidebar]")
        sys.exit(1)

    render = render_dag if sys.argv[1] == "--dag" else render_sidebar

    try:
        while True:
            render()
            time.sleep(30)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
