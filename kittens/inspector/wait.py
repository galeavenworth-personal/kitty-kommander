"""Readiness polling for kitty-kommander startup.

Blocks until a kitty-kommander instance is fully ready or the timeout
expires. Used by ``kitty +kitten inspector wait`` to gate integration
tests against startup race conditions.

Polls through four phases in order:
    1. Kitty socket accepts connections
    2. At least 4 tabs exist
    3. tmux session exists
    4. Dashboard pane has rendered content

One function:
    wait_ready(socket, session, timeout) -- True if all phases pass
"""

import sys
import time

from . import kitty_state, tmux_state

_MIN_DASHBOARD_CHARS = 20


def wait_ready(socket: str, session: str, timeout: int) -> bool:
    """Poll until a kitty-kommander instance is fully ready.

    Parameters
    ----------
    socket : str
        Kitty control socket path, e.g. ``unix:/tmp/kitty-kommander-myapp``.
    session : str
        tmux session name, e.g. ``cockpit-myapp``.
    timeout : int
        Maximum seconds to wait before giving up.

    Returns
    -------
    bool
        True if all readiness phases passed within *timeout*, False otherwise.
    """
    deadline = time.monotonic() + timeout

    # Phase 1: Socket accepts connections and returns valid tab data
    _log("Waiting for kitty socket...")
    tabs = None
    while time.monotonic() < deadline:
        try:
            result = kitty_state.ls(socket)
            tabs = result.get("tabs", [])
            _log("Socket responding.")
            break
        except ConnectionError:
            time.sleep(1)
    else:
        _log("Timed out waiting for kitty socket.")
        return False

    # Phase 2: At least 4 tabs exist
    _log("Waiting for 4 tabs...")
    while time.monotonic() < deadline:
        if len(tabs) >= 4:
            _log(f"Found {len(tabs)} tabs.")
            break
        time.sleep(1)
        try:
            tabs = kitty_state.ls(socket).get("tabs", [])
        except ConnectionError:
            pass
    else:
        _log(f"Timed out waiting for 4 tabs (have {len(tabs)}).")
        return False

    # Phase 3: tmux session exists
    _log(f"Waiting for tmux session '{session}'...")
    while time.monotonic() < deadline:
        info = tmux_state.session_info(session)
        if info.get("exists"):
            _log("tmux session ready.")
            break
        time.sleep(1)
    else:
        _log("Timed out waiting for tmux session.")
        return False

    # Phase 4: Dashboard pane has content
    _log("Waiting for dashboard content...")
    while time.monotonic() < deadline:
        try:
            content = tmux_state.capture_pane(session, "0.0")
            stripped = content.strip()
            if len(stripped) >= _MIN_DASHBOARD_CHARS:
                _log("Dashboard content detected.")
                return True
        except RuntimeError:
            pass
        time.sleep(1)

    _log("Timed out waiting for dashboard content.")
    return False


def _log(msg: str) -> None:
    """Write a status message to stderr."""
    print(f"[inspector wait] {msg}", file=sys.stderr, flush=True)
