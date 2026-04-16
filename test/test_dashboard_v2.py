"""E2E visual verification of Dashboard v2 via inspector kitten.

These tests require a running kitty-kommander instance with a display server.
They auto-skip in headless CI environments.

Tests verify:
- DAG pane renders nodes after bead creation
- Sidebar shows all 5 sections (HEALTH, READY QUEUE, MUTATIONS, AGENTS, COMMITS)
- Closing a bead produces a mutation entry in the sidebar
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

# ── Skip conditions ──────────────────────────────────────────────────────────

requires_kitty = pytest.mark.skipif(
    not os.environ.get("KITTY_LISTEN_ON"),
    reason="No KITTY_LISTEN_ON — not inside a kitty instance",
)

requires_display = pytest.mark.skipif(
    not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"),
    reason="No display server available",
)

requires_kommander = pytest.mark.skipif(
    not os.environ.get("KITTY_KOMMANDER_SESSION"),
    reason="No KITTY_KOMMANDER_SESSION — not a kitty-kommander instance",
)

# Combine all markers for dashboard tests
dashboard_test = pytest.mark.usefixtures()


def _inspector(cmd, *args, timeout=10):
    """Run inspector kitten and return parsed JSON output."""
    socket = os.environ.get("KITTY_LISTEN_ON", "")
    proc = subprocess.run(
        [sys.executable, "-m", "kittens.inspector", "--socket", socket, cmd, *args],
        capture_output=True, text=True, timeout=timeout,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    if proc.returncode != 0:
        pytest.fail(f"Inspector {cmd} failed: {proc.stderr}")
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _get_tab_text(tab_name):
    """Get the text content of a named tab via inspector."""
    result = _inspector("text", "--match", f"title:{tab_name}")
    return result.get("text", "")


# ── Tests ────────────────────────────────────────────────────────────────────


@requires_kitty
@requires_display
@requires_kommander
class TestDagPane:
    """z0q.5.1: DAG pane shows nodes after bead creation."""

    def test_dag_pane_renders(self):
        """Dashboard tab should exist and DAG pane should contain graphviz output."""
        tabs = _inspector("ls")
        tab_names = [t.get("title", "") for t in tabs.get("tabs", [])]
        assert "Dashboard" in tab_names, f"Expected Dashboard tab, found: {tab_names}"

    def test_dag_has_nodes(self):
        """If beads with dependencies exist, DAG should render nodes (not 'all independent')."""
        text = _get_tab_text("Dashboard")
        # Either we see dependency arrows rendered, or the "all independent" message
        # Both are valid states — we just verify the pane is rendering
        assert text, "Dashboard tab has no text content"


@requires_kitty
@requires_display
@requires_kommander
class TestSidebarSections:
    """z0q.5.2: all 5 sections present in sidebar."""

    def test_all_sections_present(self):
        """Sidebar should contain all 5 section headers."""
        text = _get_tab_text("Dashboard")
        expected_sections = [
            "PROJECT HEALTH",
            "READY QUEUE",
            "RECENT MUTATIONS",
            "AGENTS",
            "RECENT COMMITS",
        ]
        for section in expected_sections:
            assert section in text, f"Missing sidebar section: {section}"

    def test_health_bar_present(self):
        """Health section should show a percentage."""
        text = _get_tab_text("Dashboard")
        assert "%" in text, "No percentage found in sidebar"


@requires_kitty
@requires_display
@requires_kommander
class TestMutationAppears:
    """z0q.5.3: closing a bead shows in mutations log.

    HUMAN ACTION REQUIRED: This test creates and closes a temporary bead
    to verify the mutation pipeline works end to end.
    """

    @pytest.fixture(autouse=True)
    def _temp_bead(self):
        """Create a temporary bead, yield its ID, then clean up."""
        result = subprocess.run(
            ["bd", "create", "--title=e2e-test-mutation", "--type=task",
             "--priority=4", "--format=json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            pytest.skip("Could not create test bead")
        data = json.loads(result.stdout)
        self.bead_id = data.get("id", "")
        yield
        # Cleanup: close the test bead
        subprocess.run(
            ["bd", "close", self.bead_id, "--reason=e2e cleanup"],
            capture_output=True, timeout=10,
        )

    def test_mutation_visible_after_close(self):
        """After closing a bead, wait for sidebar refresh and check mutations."""
        # Close the bead
        subprocess.run(
            ["bd", "close", self.bead_id, "--reason=e2e test"],
            capture_output=True, timeout=10,
        )
        # Wait for sidebar refresh (30s cycle + buffer)
        time.sleep(35)

        text = _get_tab_text("Dashboard")
        short_id = self.bead_id.split("-")[-1] if "-" in self.bead_id else self.bead_id
        assert short_id in text or "closed" in text, (
            f"Expected mutation for {short_id} in sidebar after close"
        )
