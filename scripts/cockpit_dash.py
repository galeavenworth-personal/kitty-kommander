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
from helm_data import (
    build_helm_dot,
    build_helm_status_text,
    build_federation_footer,
    get_cell_topology,
    get_cell_status,
    get_cross_cell_gates,
    get_cell_mutations,
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

def capture_dag(output_path, project_dir=None):
    """Render the DAG to a PNG file (no terminal, no timg).

    This is the agentic vision loop — an agent calls this, reads the PNG
    via its vision tool, evaluates the rendering, and iterates.

    Parameters
    ----------
    output_path : str
        Destination PNG file path.
    project_dir : str, optional
        Override project directory for data fetching.

    Returns
    -------
    str or None
        The output path on success, None if no dependency chains exist.
    """
    kwargs = {"project_dir": project_dir} if project_dir else {}
    blocked = bd(["blocked"], **kwargs)
    ready = bd(["ready", "-n", "100"], **kwargs)
    all_open = bd(["list", "--status=open", "-n", "100"], **kwargs)
    wip = bd(["list", "--status=in_progress", "-n", "100"], **kwargs)

    assignee_map = {}
    for issue in wip:
        assignee = issue.get("assignee", "") or issue.get("claimed_by", "")
        if assignee:
            assignee_map[issue["id"]] = assignee

    dot_str = build_dag_dot(blocked, ready, all_open, wip, assignee_map=assignee_map)
    if dot_str is None:
        return None

    try:
        dot_proc = subprocess.Popen(
            ["dot", "-Tpng", "-Gdpi=150"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        png, _ = dot_proc.communicate(dot_str.encode(), timeout=10)
        if dot_proc.returncode != 0 or not png:
            return None

        with open(output_path, "wb") as f:
            f.write(png)
        return output_path

    except Exception:
        return None


# ── Helm Rendering ───────────────────────────────────────────────────────────

def render_helm_topology():
    """Fetch cell topology, render DOT graph via dot → timg, print footer."""
    cells = get_cell_topology()

    if not cells:
        sys.stdout.write(CLR)
        print(f"\n  {C_GREEN}Single-cell mode — no sub-cells deployed."
              f" Use cell-spawn.sh to deploy a sub-cell.{RST}")
        sys.stdout.flush()
        return

    # Build edges from parent fields (build_helm_dot does this internally,
    # but we pass None to let it handle it)
    dot_str = build_helm_dot(cells)

    if dot_str is None:
        sys.stdout.write(CLR)
        print(f"\n  {C_GREEN}No cell topology to render.{RST}")
        sys.stdout.flush()
        return

    cols, rows = term_size()
    gw = min(cols, 180)
    gh = min(rows - 6, 50)  # Leave room for federation footer

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
        return

    # Print federation sync footer below graph
    footer = build_federation_footer(cells)
    if footer:
        print(footer)
    sys.stdout.flush()


def render_helm_status():
    """Fetch cell status, gates, mutations and print status text."""
    cells = get_cell_status()
    gates = get_cross_cell_gates()
    mutations = get_cell_mutations()

    cols, _ = term_size()
    bar_w = min(cols - 6, 50)

    text = build_helm_status_text(
        cells=cells,
        gates=gates,
        mutations=mutations,
        bar_width=bar_w,
    )

    sys.stdout.write(CLR)
    print(text)

    now = datetime.now().strftime("%H:%M:%S")
    print(f"\n  {DIM}{C_GREY}Updated {now}  •  30s refresh{RST}")
    sys.stdout.flush()


# ── Helm Capture ─────────────────────────────────────────────────────────────

def capture_helm_topology(output_path, project_dir=None):
    """Render the helm topology to a PNG file (no terminal, no timg).

    Parameters
    ----------
    output_path : str
        Destination PNG file path.
    project_dir : str, optional
        Override project directory for data fetching.

    Returns
    -------
    str or None
        The output path on success, None if no cells exist.
    """
    cells = get_cell_topology(project_dir=project_dir)
    if not cells:
        return None

    dot_str = build_helm_dot(cells)
    if dot_str is None:
        return None

    try:
        dot_proc = subprocess.Popen(
            ["dot", "-Tpng", "-Gdpi=150"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        png, _ = dot_proc.communicate(dot_str.encode(), timeout=10)
        if dot_proc.returncode != 0 or not png:
            return None

        with open(output_path, "wb") as f:
            f.write(png)
        return output_path

    except Exception:
        return None


def capture_helm_status(output_path=None, project_dir=None):
    """Capture the helm status text (stripped of ANSI codes if saving to file).

    Parameters
    ----------
    output_path : str, optional
        If given, write raw text to file. Otherwise return the ANSI string.
    project_dir : str, optional
        Override project directory for data fetching.

    Returns
    -------
    str
        The status text (with ANSI codes if no output_path, stripped if saved).
    """
    import re

    cells = get_cell_status(project_dir=project_dir)
    gates = get_cross_cell_gates(project_dir=project_dir)
    mutations = get_cell_mutations(project_dir=project_dir)

    text = build_helm_status_text(
        cells=cells, gates=gates, mutations=mutations, bar_width=50,
    )

    if output_path:
        stripped = re.sub(r"\033\[[0-9;]*m", "", text)
        with open(output_path, "w") as f:
            f.write(stripped)

    return text


# ── Sidebar Capture ──────────────────────────────────────────────────────────

def capture_sidebar(output_path=None, project_dir=None):
    """Capture the sidebar text (stripped of ANSI codes if saving to file).

    Parameters
    ----------
    output_path : str, optional
        If given, write raw text to file. Otherwise return the ANSI string.
    project_dir : str, optional
        Override project directory for data fetching.

    Returns
    -------
    str
        The sidebar text (with ANSI codes if no output_path, stripped if saved).
    """
    import re

    kwargs = {"project_dir": project_dir} if project_dir else {}
    stats = bd(["stats"], **kwargs)
    ready = bd(["ready", "-n", "100"], **kwargs)
    commits = git_log(10, project_dir=project_dir)
    mutations = get_mutations(limit=8, project_dir=project_dir)
    agents = get_agents(project_dir=project_dir)

    text = build_sidebar_text(
        stats=stats, ready=ready, commits=commits,
        mutations=mutations, agents=agents, bar_width=50,
    )

    if output_path:
        stripped = re.sub(r"\033\[[0-9;]*m", "", text)
        with open(output_path, "w") as f:
            f.write(stripped)

    return text


def main():
    USAGE = (
        "Usage: cockpit_dash.py [--dag | --sidebar | --helm-topology | --helm-status"
        " | --capture-dag FILE | --capture-sidebar FILE"
        " | --capture-helm-topology FILE | --capture-helm-status FILE]"
    )

    if len(sys.argv) < 2:
        print(USAGE)
        sys.exit(1)

    arg = sys.argv[1]

    # ── One-shot capture modes ──
    if arg == "--capture-dag":
        path = sys.argv[2] if len(sys.argv) > 2 else "test-artifacts/dag_capture.png"
        project = sys.argv[3] if len(sys.argv) > 3 else None
        result = capture_dag(path, project_dir=project)
        if result:
            print(f"DAG captured: {result}")
        else:
            print("No dependency chains to render.")
        return

    if arg == "--capture-sidebar":
        path = sys.argv[2] if len(sys.argv) > 2 else "test-artifacts/sidebar_capture.txt"
        project = sys.argv[3] if len(sys.argv) > 3 else None
        capture_sidebar(path, project_dir=project)
        print(f"Sidebar captured: {path}")
        return

    if arg == "--capture-helm-topology":
        path = sys.argv[2] if len(sys.argv) > 2 else "test-artifacts/helm_topology.png"
        project = sys.argv[3] if len(sys.argv) > 3 else None
        result = capture_helm_topology(path, project_dir=project)
        if result:
            print(f"Helm topology captured: {result}")
        else:
            print("No cells to render (single-cell mode).")
        return

    if arg == "--capture-helm-status":
        path = sys.argv[2] if len(sys.argv) > 2 else "test-artifacts/helm_status.txt"
        project = sys.argv[3] if len(sys.argv) > 3 else None
        capture_helm_status(path, project_dir=project)
        print(f"Helm status captured: {path}")
        return

    # ── Auto-refresh render modes ──
    render_modes = {
        "--dag": render_dag,
        "--sidebar": render_sidebar,
        "--helm-topology": render_helm_topology,
        "--helm-status": render_helm_status,
    }

    render = render_modes.get(arg)
    if render is None:
        print(USAGE)
        sys.exit(1)

    try:
        while True:
            render()
            time.sleep(30)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
