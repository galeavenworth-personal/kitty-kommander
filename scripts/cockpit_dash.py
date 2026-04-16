#!/usr/bin/env python3
"""Cockpit dashboard — beads DAG + project health for the Kitty terminal.

Usage:
    cockpit_dash.py --dag       # Left pane: dependency graph (graphviz → timg)
    cockpit_dash.py --sidebar   # Right pane: stats + ready queue + activity

Auto-refreshes every 30 seconds. Ctrl-C to exit.

All data fetching and pure logic lives in dash_data.py.
This module handles only rendering (subprocess calls to dot/timg, ANSI output).
"""

import shutil
import subprocess
import sys
import time
from datetime import datetime

from dash_data import (
    PAL,
    bd,
    build_dag_dot,
    build_sidebar_text,
    get_agents,
    get_mutations,
    git_log,
)

# ── ANSI Helpers ──────────────────────────────────────────────────────────────

TIMG = "/usr/bin/timg"


def ansi(hex_color):
    r, g, b = int(hex_color[1:3], 16), int(hex_color[3:5], 16), int(hex_color[5:7], 16)
    return f"\033[38;2;{r};{g};{b}m"


RST = "\033[0m"
CLR = "\033[2J\033[H"
DIM = "\033[2m"

C_RED = ansi(PAL["red"])
C_GREEN = ansi(PAL["green"])
C_GREY = ansi(PAL["grey"])


def term_size():
    return shutil.get_terminal_size((120, 40))


# ── DAG Rendering ─────────────────────────────────────────────────────────────

def render_dag():
    """Fetch data, generate DOT via pure function, render through dot → timg."""
    blocked = bd(["blocked"])
    ready = bd(["ready", "-n", "100"])
    all_open = bd(["list", "--status=open", "-n", "100"])
    wip = bd(["list", "--status=in_progress", "-n", "100"])

    # Build assignee map for kitty badge overlays
    assignee_map = {}
    for issue in wip:
        assignee = issue.get("assignee", "") or issue.get("claimed_by", "")
        if assignee:
            assignee_map[issue["id"]] = assignee

    dot_str = build_dag_dot(blocked, ready, all_open, wip, assignee_map=assignee_map)

    if dot_str is None:
        sys.stdout.write(CLR)
        print(f"\n  {C_GREEN}No dependency chains — all issues independent.{RST}")
        sys.stdout.flush()
        return

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
    """Fetch all data, generate sidebar text via pure function, print."""
    stats = bd(["stats"])
    ready = bd(["ready", "-n", "100"])
    commits = git_log(10)
    mutations = get_mutations(limit=8)
    agents = get_agents()

    cols, _ = term_size()
    bar_w = min(cols - 6, 50)

    text = build_sidebar_text(
        stats=stats,
        ready=ready,
        commits=commits,
        mutations=mutations,
        agents=agents,
        bar_width=bar_w,
    )

    sys.stdout.write(CLR)
    print(text)

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
