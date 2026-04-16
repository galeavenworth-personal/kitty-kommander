"""Pytest fixtures for kitty-kommander integration tests.

Provides the ``kommander`` fixture that launches a kitty-kommander instance,
waits for readiness, yields an InspectorHandle for test assertions, and
tears down cleanly on exit.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

# Make kittens.inspector importable from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kittens.inspector import kitty_state, tmux_state, capture, desktop, wait

# ---------------------------------------------------------------------------
# Skip markers
# ---------------------------------------------------------------------------

requires_kitty = pytest.mark.skipif(
    not shutil.which("kitty"),
    reason="kitty not installed",
)

requires_display = pytest.mark.skipif(
    not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
    reason="no display server",
)


# ---------------------------------------------------------------------------
# Handle
# ---------------------------------------------------------------------------

@dataclass
class InspectorHandle:
    """Convenience wrapper around a running kitty-kommander instance."""

    proc: subprocess.Popen
    socket: str
    session: str
    dir: Path

    def tabs(self) -> dict:
        """Tab/window tree from kitty."""
        return kitty_state.ls(self.socket)

    def get_text(self, match: str, ansi: bool = False) -> str:
        """Screen text from a kitty window matching *match*."""
        return kitty_state.get_text(self.socket, match, ansi)

    def tmux(self) -> dict:
        """tmux session structure."""
        return tmux_state.session_info(self.session)

    def tmux_text(self, pane: str = "0.0", ansi: bool = False) -> str:
        """Captured text from a tmux pane."""
        return tmux_state.capture_pane(self.session, pane, ansi)

    def screenshot(
        self,
        output: str,
        tab: str = None,
        pane: str = None,
    ) -> str:
        """Capture a PNG screenshot, optionally focusing a tab/pane first."""
        if tab or pane:
            return capture.focus_and_capture(self.socket, output, tab=tab, pane=pane)
        return capture.screenshot_focused_window(output)

    def desktop(self) -> dict:
        """Desktop integration status."""
        return desktop.check()


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@requires_kitty
@requires_display
@pytest.fixture(scope="function")
def kommander(tmp_path):
    """Launch a kitty-kommander instance and yield an InspectorHandle.

    The fixture:
    1. Initialises a throwaway beads repo in *tmp_path*.
    2. Starts ``kitty-kommander <tmp_path>`` as a subprocess.
    3. Waits up to 30 s for kitty + tmux to be fully ready.
    4. Yields an ``InspectorHandle`` with convenience inspection methods.
    5. Tears down the kitty process and tmux session on cleanup.
    """
    # Initialise beads in the temp project dir (failure is non-fatal).
    subprocess.run(
        ["bd", "init"],
        cwd=tmp_path,
        capture_output=True,
    )

    slug = tmp_path.name
    socket = f"unix:/tmp/kitty-kommander-{slug}"
    session = f"cockpit-{slug}"

    proc = subprocess.Popen(
        ["kitty-kommander", str(tmp_path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        ready = wait.wait_ready(socket, session, timeout=30)
        if not ready:
            raise RuntimeError(
                f"kitty-kommander did not become ready within 30 s "
                f"(socket={socket}, session={session})"
            )

        yield InspectorHandle(proc=proc, socket=socket, session=session, dir=tmp_path)

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

        subprocess.run(
            ["tmux", "kill-session", "-t", session],
            capture_output=True,
        )
