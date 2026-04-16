"""Tests for parallel kitty-kommander instance isolation.

Verifies that two kitty-kommander instances launched on different project
directories get independent sockets, tmux sessions, tab trees, and PIDs.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kittens.inspector import _scan_sockets, wait as inspector_wait, tmux_state

# Re-use the InspectorHandle from conftest so we get the same interface.
from conftest import InspectorHandle

requires_kitty = pytest.mark.skipif(
    not shutil.which("kitty"), reason="kitty not installed"
)


@pytest.fixture
def launch_pair(tmp_path):
    """Launch two kitty-kommander instances on different project dirs."""
    dir_a = tmp_path / "alpha"
    dir_b = tmp_path / "beta"
    dir_a.mkdir()
    dir_b.mkdir()

    # Init beads in each (failure is non-fatal).
    subprocess.run(["bd", "init"], cwd=dir_a, capture_output=True)
    subprocess.run(["bd", "init"], cwd=dir_b, capture_output=True)

    sock_a = f"unix:/tmp/kitty-kommander-{dir_a.name}"
    sock_b = f"unix:/tmp/kitty-kommander-{dir_b.name}"
    sess_a = f"cockpit-{dir_a.name}"
    sess_b = f"cockpit-{dir_b.name}"

    proc_a = subprocess.Popen(
        ["kitty-kommander", str(dir_a)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    proc_b = subprocess.Popen(
        ["kitty-kommander", str(dir_b)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        inspector_wait.wait_ready(sock_a, sess_a, 30)
        inspector_wait.wait_ready(sock_b, sess_b, 30)

        handle_a = InspectorHandle(proc=proc_a, socket=sock_a, session=sess_a, dir=dir_a)
        handle_b = InspectorHandle(proc=proc_b, socket=sock_b, session=sess_b, dir=dir_b)

        yield handle_a, handle_b

    finally:
        for p in (proc_a, proc_b):
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=5)
        for s in (sess_a, sess_b):
            subprocess.run(["tmux", "kill-session", "-t", s], capture_output=True)


@requires_kitty
class TestParallel:
    """Isolation assertions for two concurrent kitty-kommander instances."""

    def test_two_instances_different_sockets(self, launch_pair):
        """Each instance must use a distinct kitty control socket."""
        handle_a, handle_b = launch_pair
        assert handle_a.socket != handle_b.socket

    def test_two_instances_different_tmux_sessions(self, launch_pair):
        """Both tmux session names must appear in the global session list."""
        handle_a, handle_b = launch_pair
        sessions = tmux_state.list_sessions()
        assert handle_a.session in sessions
        assert handle_b.session in sessions

    def test_two_instances_independent_tabs(self, launch_pair):
        """Each instance must report its own four-tab layout."""
        handle_a, handle_b = launch_pair
        tabs_a = handle_a.tabs()
        tabs_b = handle_b.tabs()
        assert len(tabs_a["tabs"]) == 4
        assert len(tabs_b["tabs"]) == 4

    def test_two_instances_independent_pids(self, launch_pair):
        """The first window PID in tab 0 must differ between instances."""
        handle_a, handle_b = launch_pair
        pid_a = handle_a.tabs()["tabs"][0]["windows"][0]["pid"]
        pid_b = handle_b.tabs()["tabs"][0]["windows"][0]["pid"]
        assert pid_a != pid_b

    def test_sockets_subcommand(self, launch_pair):
        """_scan_sockets must find both instance sockets and report them responding."""
        handle_a, handle_b = launch_pair
        results = _scan_sockets()

        # Extract just the socket file paths (without unix: prefix).
        sock_a_path = handle_a.socket.removeprefix("unix:")
        sock_b_path = handle_b.socket.removeprefix("unix:")

        found = {r["socket"]: r for r in results}
        assert sock_a_path in found, f"socket {sock_a_path} not found in scan results"
        assert sock_b_path in found, f"socket {sock_b_path} not found in scan results"
        assert found[sock_a_path]["responding"] is True
        assert found[sock_b_path]["responding"] is True
