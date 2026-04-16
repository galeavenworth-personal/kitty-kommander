"""Kitty remote control wrappers for the Inspector Kitten.

Provides structured inspection of kitty terminal state by wrapping
kitty's remote control protocol (kitten @). Used by wait.py for
readiness polling and by integration tests for layout verification.

Two functions:
    ls(socket)              -- tab/window tree as simplified dict
    get_text(socket, match) -- screen content from a matched window
"""

import json
import subprocess


def ls(socket: str) -> dict:
    """Query kitty's tab/window tree via ``kitten @ ls``.

    Parameters
    ----------
    socket : str
        Full kitty control socket path, e.g. ``unix:/tmp/kitty-kommander-myapp``.

    Returns
    -------
    dict
        Simplified structure::

            {
                "tabs": [
                    {
                        "index": 0,
                        "title": "Cockpit",
                        "layout": "tall",
                        "is_focused": False,
                        "windows": [
                            {"title": "tmux", "pid": 12345, "cwd": "/home/user/project"}
                        ]
                    },
                    ...
                ]
            }

    Raises
    ------
    ConnectionError
        If kitty is unreachable at the given socket.
    """
    try:
        result = subprocess.run(
            ["kitten", "@", "ls", "--to", socket],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise ConnectionError(
            f"Cannot connect to kitty at {socket}: {exc}"
        ) from exc

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ConnectionError(
            f"Cannot connect to kitty at {socket}: invalid JSON response"
        ) from exc

    # kitten @ ls returns a list of OS windows, each containing a "tabs" key.
    # Typically one OS window per kitty instance. Flatten by taking the first.
    if not raw:
        return {"tabs": []}

    os_window = raw[0]
    tabs = []

    for idx, tab in enumerate(os_window.get("tabs", [])):
        windows = []
        for win in tab.get("windows", []):
            # foreground_processes is a list; take the first PID if available
            fg = win.get("foreground_processes", [])
            pid = fg[0].get("pid") if fg else None

            windows.append({
                "title": win.get("title", ""),
                "pid": pid,
                "cwd": win.get("cwd", ""),
            })

        tabs.append({
            "index": idx,
            "title": tab.get("title", ""),
            "layout": tab.get("layout", ""),
            "is_focused": tab.get("is_focused", False),
            "windows": windows,
        })

    return {"tabs": tabs}


def get_text(socket: str, match: str, ansi: bool = False) -> str:
    """Read screen content from a kitty window via ``kitten @ get-text``.

    Parameters
    ----------
    socket : str
        Full kitty control socket path, e.g. ``unix:/tmp/kitty-kommander-myapp``.
    match : str
        Kitty match expression, e.g. ``"title:Dashboard"``.
    ansi : bool, optional
        If True, include ANSI escape sequences in the output (default False).

    Returns
    -------
    str
        The text content of the matched window, with trailing whitespace stripped.

    Raises
    ------
    ConnectionError
        If kitty is unreachable at the given socket.
    """
    cmd = ["kitten", "@", "get-text", "--to", socket, "--match", match]
    if ansi:
        cmd.append("--ansi")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise ConnectionError(
            f"Cannot connect to kitty at {socket}: {exc}"
        ) from exc

    return result.stdout.rstrip()
