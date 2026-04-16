"""Tests for kitty-kommander session structure — tab layout, tmux, env vars.

Verifies that a launched kitty-kommander instance has the expected four-tab
layout, correct tab names, tmux session binding, and that the Driver tab
is running Claude Code.
"""

import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.mark.skipif(not shutil.which("kitty"), reason="kitty not installed")
class TestStructure:
    """Structural assertions against a running kitty-kommander instance."""

    def test_four_tabs_created(self, kommander):
        """Exactly four tabs must exist after startup."""
        tabs = kommander.tabs()
        assert len(tabs["tabs"]) == 4

    def test_tab_names(self, kommander):
        """Tabs must be named Cockpit, Driver, Notebooks, Dashboard (in order)."""
        tabs = kommander.tabs()
        names = [t["title"] for t in tabs["tabs"]]
        assert names == ["Cockpit", "Driver", "Notebooks", "Dashboard"]

    def test_driver_tab_focused(self, kommander):
        """The Driver tab (index 1) must be the focused tab on startup."""
        tabs = kommander.tabs()
        assert tabs["tabs"][1]["is_focused"] is True

    def test_dashboard_has_two_windows(self, kommander):
        """The Dashboard tab must have two windows (DAG + sidebar split)."""
        tabs = kommander.tabs()
        dashboard = tabs["tabs"][3]
        assert len(dashboard["windows"]) == 2

    def test_tmux_session_exists(self, kommander):
        """The tmux session backing the Cockpit tab must exist."""
        info = kommander.tmux()
        assert info["exists"] is True

    def test_tmux_session_name_matches_slug(self, kommander):
        """The tmux session name must follow the cockpit-<slug> convention."""
        info = kommander.tmux()
        expected = f"cockpit-{kommander.dir.name}"
        assert info["session"] == expected

    def test_env_var_expanded(self, kommander):
        """The session name must not be the bare literal 'cockpit' (env var must expand)."""
        info = kommander.tmux()
        assert info["session"] != "cockpit"

    def test_driver_runs_claude(self, kommander):
        """The Driver tab's screen content must contain 'claude' (case-insensitive)."""
        text = kommander.get_text("title:Driver")
        assert "claude" in text.lower()
