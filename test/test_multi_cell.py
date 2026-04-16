"""Tests for multi-cell lifecycle — spawn, federation, gates, teardown.

Integration tests require a running kitty instance and display server.
Headless tests (test_teardown_safety_check) run anywhere.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Repo root (parent of test/)
REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"

# Make kittens.inspector importable
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Skip markers (mirrors conftest.py)
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
# Helpers
# ---------------------------------------------------------------------------

def slug_from_dir(d: Path) -> str:
    """Mirror the slug derivation from launch-cockpit.sh."""
    return d.name.lower().strip("-")


def run_script(name: str, *args, check: bool = True, cwd=None, **kwargs):
    """Run a script from the scripts/ directory."""
    return subprocess.run(
        [str(SCRIPTS / name), *args],
        capture_output=True,
        text=True,
        check=check,
        cwd=cwd,
        **kwargs,
    )


def teardown_cell(cell_name: str, project_dir: Path):
    """Best-effort teardown of a sub-cell — ignore errors."""
    try:
        run_script(
            "cell-teardown.sh", cell_name, str(project_dir), "--force",
            check=False,
        )
    except Exception:
        pass

    # Belt-and-suspenders: kill tmux session and socket if still lingering
    slug = slug_from_dir(project_dir)
    subprocess.run(
        ["tmux", "kill-session", "-t", f"cockpit-{slug}"],
        capture_output=True,
    )
    socket_path = Path(f"/tmp/kitty-kommander-{slug}")
    if socket_path.exists():
        socket_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_cell_dir(tmp_path):
    """Create a temp directory for a test sub-cell with beads initialized."""
    cell_dir = tmp_path / "test-subcell"
    cell_dir.mkdir()
    subprocess.run(["bd", "init"], cwd=cell_dir, capture_output=True, check=True)
    yield cell_dir


@pytest.fixture
def spawned_cell(test_cell_dir):
    """Spawn a sub-cell and yield (cell_dir, metadata_dict). Teardown after."""
    result = run_script("cell-spawn.sh", str(test_cell_dir), "test-alpha")
    meta = json.loads(result.stdout.strip())
    yield test_cell_dir, meta
    teardown_cell("test-alpha", test_cell_dir)


# ---------------------------------------------------------------------------
# Test 1 & 2: Spawn + Federation (requires kitty + display)
# ---------------------------------------------------------------------------

@requires_kitty
@requires_display
class TestCellSpawnAndFederation:
    """Verify cell-spawn.sh launches a sub-cell and registers federation peers."""

    def test_spawn_returns_valid_json(self, spawned_cell):
        """cell-spawn.sh must return JSON with all expected fields."""
        _cell_dir, meta = spawned_cell
        assert "cell_name" in meta
        assert "project_dir" in meta
        assert "socket" in meta
        assert "session" in meta
        assert "slug" in meta
        assert meta["cell_name"] == "test-alpha"

    def test_spawn_json_matches_slug_convention(self, spawned_cell):
        """Socket and session must follow the slug convention."""
        cell_dir, meta = spawned_cell
        slug = slug_from_dir(cell_dir)
        assert meta["slug"] == slug
        assert meta["socket"] == f"unix:/tmp/kitty-kommander-{slug}"
        assert meta["session"] == f"cockpit-{slug}"

    def test_parent_has_subcell_peer(self, spawned_cell):
        """Parent's federation peers must include the sub-cell."""
        _cell_dir, _meta = spawned_cell
        result = subprocess.run(
            ["bd", "federation", "list-peers", "--json"],
            capture_output=True, text=True, check=True,
        )
        peers = json.loads(result.stdout)
        peer_names = [p.get("name", p.get("Name", "")) for p in peers]
        assert "test-alpha" in peer_names

    def test_subcell_has_parent_peer(self, spawned_cell):
        """Sub-cell's federation peers must include 'parent'."""
        cell_dir, _meta = spawned_cell
        result = subprocess.run(
            ["bd", "federation", "list-peers", "--json"],
            capture_output=True, text=True, check=True,
            cwd=cell_dir,
        )
        peers = json.loads(result.stdout)
        peer_names = [p.get("name", p.get("Name", "")) for p in peers]
        assert "parent" in peer_names


# ---------------------------------------------------------------------------
# Test 3: Cross-cell gate lifecycle (requires kitty + display)
# ---------------------------------------------------------------------------

@requires_kitty
@requires_display
class TestCrossCellGateLifecycle:
    """Verify gate creation, check, and resolution across cells."""

    def test_gate_create_and_resolve(self, spawned_cell):
        """Create a gate, close the blocking bead, verify resolution."""
        cell_dir, _meta = spawned_cell

        # Create a bead in parent
        parent_result = subprocess.run(
            ["bd", "create", "test-gate-parent", "-t", "task", "--json"],
            capture_output=True, text=True, check=True,
        )
        parent_bead = json.loads(parent_result.stdout)
        parent_bead_id = parent_bead.get("id", parent_bead.get("Id", ""))
        assert parent_bead_id, "Failed to get parent bead ID"

        # Create a bead in sub-cell
        child_result = subprocess.run(
            ["bd", "create", "test-gate-child", "-t", "task", "--json"],
            capture_output=True, text=True, check=True,
            cwd=cell_dir,
        )
        child_bead = json.loads(child_result.stdout)
        child_bead_id = child_bead.get("id", child_bead.get("Id", ""))
        assert child_bead_id, "Failed to get child bead ID"

        # Create cross-cell gate
        gate_result = run_script(
            "cell-gate.sh", "create", parent_bead_id, "test-alpha", child_bead_id,
            check=True,
        )

        # Verify gate exists in list
        list_result = run_script("cell-gate.sh", "list", check=True)
        list_output = list_result.stdout
        assert parent_bead_id in list_output

        # Close the child bead in sub-cell
        subprocess.run(
            ["bd", "close", child_bead_id, "--reason", "test complete"],
            capture_output=True, text=True, check=True,
            cwd=cell_dir,
        )

        # Sync and check
        check_result = run_script("cell-gate.sh", "check", "--type=bead", check=False)
        # After closing the blocker and syncing, the gate should resolve.
        # We verify by checking the list again — gate should no longer appear
        # (or appear as resolved).
        list_after = run_script("cell-gate.sh", "list", check=False)
        # If the gate resolved, parent_bead_id should not appear in open gates
        # (it may still appear with --all, but the default list shows only open)
        assert parent_bead_id not in list_after.stdout or "resolved" in list_after.stdout.lower()

        # Clean up parent bead
        subprocess.run(
            ["bd", "close", parent_bead_id, "--reason", "test cleanup"],
            capture_output=True, text=True, check=False,
        )


# ---------------------------------------------------------------------------
# Test 4: Teardown cleans up (requires kitty + display)
# ---------------------------------------------------------------------------

@requires_kitty
@requires_display
class TestTeardownCleansUp:
    """Verify cell-teardown.sh removes peers, session, and socket."""

    def test_teardown_removes_all_traces(self, test_cell_dir):
        """After teardown, federation peer, tmux session, and socket must be gone."""
        # Spawn
        result = run_script("cell-spawn.sh", str(test_cell_dir), "test-gamma")
        meta = json.loads(result.stdout.strip())
        slug = meta["slug"]

        # Teardown with --force
        run_script(
            "cell-teardown.sh", "test-gamma", str(test_cell_dir), "--force",
            check=True,
        )

        # Verify: federation peer removed from parent
        peer_result = subprocess.run(
            ["bd", "federation", "list-peers", "--json"],
            capture_output=True, text=True, check=True,
        )
        peers = json.loads(peer_result.stdout)
        peer_names = [p.get("name", p.get("Name", "")) for p in peers]
        assert "test-gamma" not in peer_names

        # Verify: tmux session gone
        tmux_result = subprocess.run(
            ["tmux", "has-session", "-t", f"cockpit-{slug}"],
            capture_output=True,
        )
        assert tmux_result.returncode != 0, "tmux session should not exist after teardown"

        # Verify: socket file gone
        assert not Path(f"/tmp/kitty-kommander-{slug}").exists()


# ---------------------------------------------------------------------------
# Test 5: Teardown safety check (headless — no kitty needed)
# ---------------------------------------------------------------------------

class TestTeardownSafetyCheck:
    """Verify teardown refuses to proceed when open beads exist (no --force)."""

    def test_refuses_with_open_items(self, test_cell_dir):
        """cell-teardown.sh without --force must fail if there are open beads."""
        # Create an open bead in the test cell
        subprocess.run(
            ["bd", "create", "open-blocker", "-t", "task"],
            capture_output=True, text=True, check=True,
            cwd=test_cell_dir,
        )

        # Run teardown WITHOUT --force
        result = run_script(
            "cell-teardown.sh", "test-beta", str(test_cell_dir),
            check=False,
        )

        # Must exit non-zero
        assert result.returncode != 0, "teardown should fail with open items and no --force"

        # Stderr must mention open items
        assert "open" in result.stderr.lower() or "in-progress" in result.stderr.lower()
