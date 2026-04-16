"""tmux session inspection wrappers for the Inspector Kitten.

Provides structured access to tmux session state — existence checks,
window/pane enumeration, pane content capture, and session listing.
Used by wait.py to check tmux readiness on the critical startup path.

All commands use subprocess.run with a 10-second timeout. Returns plain
dicts/lists parsed from tmux format-string output.
"""

import subprocess


def session_info(session_name: str) -> dict:
    """Check if a tmux session exists and return its structure.

    Returns a dict with keys: session, exists, windows.
    Each window contains index, name, and a list of panes.
    Each pane contains index, command, pid, and size.
    """
    # Check if session exists
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        return {"session": session_name, "exists": False, "windows": []}
    except subprocess.TimeoutExpired:
        return {"session": session_name, "exists": False, "windows": []}

    if result.returncode != 0:
        return {"session": session_name, "exists": False, "windows": []}

    # List windows
    try:
        win_result = subprocess.run(
            [
                "tmux", "list-windows",
                "-t", session_name,
                "-F", "#{window_index}|#{window_name}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"session": session_name, "exists": True, "windows": []}

    if win_result.returncode != 0:
        return {"session": session_name, "exists": True, "windows": []}

    windows = []
    for line in win_result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        win_index = int(parts[0])
        win_name = parts[1]

        # List panes for this window
        panes = []
        try:
            pane_result = subprocess.run(
                [
                    "tmux", "list-panes",
                    "-t", f"{session_name}:{win_index}",
                    "-F", "#{pane_index}|#{pane_current_command}|#{pane_pid}|#{pane_width}x#{pane_height}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pane_result = None

        if pane_result and pane_result.returncode == 0:
            for pane_line in pane_result.stdout.strip().splitlines():
                if not pane_line:
                    continue
                pane_parts = pane_line.split("|", 3)
                if len(pane_parts) != 4:
                    continue
                panes.append({
                    "index": int(pane_parts[0]),
                    "command": pane_parts[1],
                    "pid": int(pane_parts[2]),
                    "size": pane_parts[3],
                })

        windows.append({
            "index": win_index,
            "name": win_name,
            "panes": panes,
        })

    return {
        "session": session_name,
        "exists": True,
        "windows": windows,
    }


def capture_pane(session_name: str, pane: str = "0.0", ansi: bool = False) -> str:
    """Capture the text content of a tmux pane.

    Args:
        session_name: The tmux session name.
        pane: Window.pane identifier, e.g. "0.0" for window 0, pane 0.
        ansi: If True, include ANSI escape sequences in the output.

    Returns:
        The pane text content as a string.

    Raises:
        RuntimeError: If the session or pane doesn't exist.
    """
    cmd = ["tmux", "capture-pane", "-p", "-t", f"{session_name}:{pane}"]
    if ansi:
        cmd.insert(3, "-e")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError("tmux is not installed or not on PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Timed out capturing pane {pane} in session {session_name}"
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            f"Failed to capture pane {pane} in session {session_name}: {stderr}"
        )

    return result.stdout


def list_sessions() -> list[str]:
    """List all tmux session names.

    Returns an empty list if the tmux server isn't running.
    """
    try:
        result = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        return []
    except subprocess.TimeoutExpired:
        return []

    if result.returncode != 0:
        # tmux server not running returns non-zero
        return []

    sessions = []
    for line in result.stdout.strip().splitlines():
        if line:
            sessions.append(line)
    return sessions
