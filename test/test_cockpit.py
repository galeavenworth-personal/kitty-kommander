"""Tests for Cockpit tab content — tmux pane state and teammate spawning.

The Cockpit tab (index 0) runs a tmux session where agent teammates get
panes. These tests use the inspector's tmux/tmux-text capabilities to
verify pane state, which prior tests never checked.

Three tiers:
- Headless: exercises cockpit-panes.sh against a bare tmux session (no kitty).
  Run with: pytest test/test_cockpit.py -k Headless --noconftest
- Baseline: verify the Cockpit has a working tmux session with at least one pane.
- Spawn: verify cockpit-panes.sh creates panes in a full kitty-kommander instance.
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"

requires_tmux = pytest.mark.skipif(
    not shutil.which("tmux"), reason="tmux not installed"
)
requires_kitty = pytest.mark.skipif(
    not shutil.which("kitty"), reason="kitty not installed"
)
requires_display = pytest.mark.skipif(
    not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
    reason="no display server",
)


# ---------------------------------------------------------------------------
# Headless tests — bare tmux, no kitty needed
# Run: pytest test/test_cockpit.py -k Headless --noconftest -v
# ---------------------------------------------------------------------------


@requires_tmux
class TestCockpitPanesHeadless:
    """Exercise cockpit-panes.sh against a bare tmux session (no kitty)."""

    SCRIPT = SCRIPTS / "cockpit-panes.sh"

    @pytest.fixture(autouse=True)
    def tmux_session(self):
        """Create a throwaway tmux session and tear it down after each test."""
        self.session = f"test-cockpit-{os.getpid()}"
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session],
            check=True, capture_output=True, timeout=5,
        )
        yield
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session],
            capture_output=True, timeout=5,
        )

    def _run(self, agents):
        """Run cockpit-panes.sh and return the CompletedProcess."""
        return subprocess.run(
            [str(self.SCRIPT)] + agents,
            env={**os.environ, "KITTY_KOMMANDER_SESSION": self.session},
            capture_output=True, text=True, timeout=10,
        )

    def _pane_titles(self):
        """Return list of pane titles in window 0."""
        r = subprocess.run(
            ["tmux", "list-panes", "-t", f"{self.session}:0", "-F", "#{pane_title}"],
            capture_output=True, text=True, timeout=5,
        )
        return [t.strip() for t in r.stdout.strip().splitlines() if t.strip()]

    def _pane_count(self):
        """Return number of panes in window 0."""
        return len(self._pane_titles())

    def _pane_text(self, pane="0.0"):
        """Capture text content of a pane."""
        r = subprocess.run(
            ["tmux", "capture-pane", "-p", "-t", f"{self.session}:{pane}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout

    def test_script_exists(self):
        """cockpit-panes.sh must exist and be executable."""
        assert self.SCRIPT.exists()
        assert os.access(self.SCRIPT, os.X_OK)

    def test_two_agents(self):
        """Spawning 2 agents produces 2 panes with correct titles."""
        result = self._run(["builder-1", "scout-1"])
        assert result.returncode == 0, result.stderr
        assert self._pane_count() == 2
        titles = self._pane_titles()
        assert "builder-1" in titles
        assert "scout-1" in titles

    def test_four_agents(self):
        """Spawning 4 agents produces 4 panes."""
        result = self._run(["builder-1", "builder-2", "scout-1", "critic-1"])
        assert result.returncode == 0, result.stderr
        assert self._pane_count() == 4

    def test_single_agent(self):
        """Spawning 1 agent produces 1 pane."""
        result = self._run(["builder-1"])
        assert result.returncode == 0, result.stderr
        assert self._pane_count() == 1
        assert "builder-1" in self._pane_titles()

    def test_idempotent(self):
        """Running twice with same agents doesn't duplicate panes."""
        self._run(["builder-1", "scout-1"])
        self._run(["builder-1", "scout-1"])
        assert self._pane_count() == 2

    def test_pane_text_contains_agent_name(self):
        """Each pane's text should show the agent name banner."""
        self._run(["builder-1", "scout-1"])
        time.sleep(0.5)
        text0 = self._pane_text("0.0")
        text1 = self._pane_text("0.1")
        assert "builder-1" in text0, f"Pane 0.0:\n{text0[:200]}"
        assert "scout-1" in text1, f"Pane 0.1:\n{text1[:200]}"

    def test_no_args_fails(self):
        """cockpit-panes.sh with no arguments should exit non-zero."""
        result = subprocess.run(
            [str(self.SCRIPT)],
            env={**os.environ, "KITTY_KOMMANDER_SESSION": self.session},
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0

    def test_missing_session_fails(self):
        """cockpit-panes.sh without KITTY_KOMMANDER_SESSION should fail."""
        env = {k: v for k, v in os.environ.items() if k != "KITTY_KOMMANDER_SESSION"}
        result = subprocess.run(
            [str(self.SCRIPT), "builder-1"],
            env=env,
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# Integration tests — require running kitty + display
# ---------------------------------------------------------------------------


@requires_kitty
@requires_display
class TestCockpitBaseline:
    """Verify the Cockpit tmux session has a working pane at startup."""

    def test_tmux_has_at_least_one_window(self, kommander):
        """The Cockpit tmux session must have at least one window."""
        info = kommander.tmux()
        assert info["exists"], "tmux session does not exist"
        assert len(info["windows"]) >= 1, "tmux session has no windows"

    def test_tmux_first_window_has_pane(self, kommander):
        """The first tmux window must have at least one pane (the initial shell)."""
        info = kommander.tmux()
        assert info["exists"]
        assert len(info["windows"]) >= 1
        first_window = info["windows"][0]
        assert len(first_window["panes"]) >= 1, "first window has no panes"

    def test_tmux_pane_is_running_shell(self, kommander):
        """The initial Cockpit pane should be running a shell (bash/zsh/sh)."""
        info = kommander.tmux()
        pane = info["windows"][0]["panes"][0]
        cmd = pane["command"].lower()
        assert any(
            shell in cmd for shell in ("bash", "zsh", "sh", "fish")
        ), f"Expected a shell, got: {pane['command']}"

    def test_tmux_pane_text_is_readable(self, kommander):
        """The inspector's tmux_text method must return content without error."""
        text = kommander.tmux_text(pane="0.0")
        # Just verify we got a string back (empty shell is fine at baseline)
        assert isinstance(text, str)


@requires_kitty
@requires_display
class TestCockpitPaneSpawn:
    """Verify that cockpit-panes.sh creates teammate panes correctly."""

    def _spawn_panes(self, kommander, agents):
        """Helper: call cockpit-panes.sh to create panes.

        Args:
            kommander: InspectorHandle instance.
            agents: list of agent name strings, e.g. ["builder-1", "scout-1"]
        """
        script = Path(__file__).resolve().parent.parent / "scripts" / "cockpit-panes.sh"
        assert script.exists(), f"cockpit-panes.sh not found at {script}"

        result = subprocess.run(
            [str(script)] + agents,
            env={
                **os.environ,
                "KITTY_KOMMANDER_SESSION": kommander.session,
            },
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"cockpit-panes.sh failed (exit {result.returncode}): {result.stderr}"
        )

    def test_spawn_creates_expected_pane_count(self, kommander):
        """Spawning 2 agents should produce 2 panes (replacing the initial shell)."""
        self._spawn_panes(kommander, ["builder-1", "scout-1"])
        info = kommander.tmux()
        # All agent panes land in window 0
        panes = info["windows"][0]["panes"]
        assert len(panes) == 2, f"Expected 2 panes, got {len(panes)}: {panes}"

    def test_spawn_four_agents_produces_grid(self, kommander):
        """Spawning 4 agents should produce 4 panes (2x2 grid)."""
        self._spawn_panes(kommander, ["builder-1", "builder-2", "scout-1", "critic-1"])
        info = kommander.tmux()
        panes = info["windows"][0]["panes"]
        assert len(panes) == 4, f"Expected 4 panes, got {len(panes)}: {panes}"

    def test_spawn_single_agent(self, kommander):
        """Spawning 1 agent should produce 1 pane."""
        self._spawn_panes(kommander, ["builder-1"])
        info = kommander.tmux()
        panes = info["windows"][0]["panes"]
        assert len(panes) == 1, f"Expected 1 pane, got {len(panes)}: {panes}"

    def test_pane_titles_contain_agent_names(self, kommander):
        """Each pane's title should contain the agent's name."""
        agents = ["builder-1", "scout-1"]
        self._spawn_panes(kommander, agents)

        # Read pane titles via tmux
        result = subprocess.run(
            [
                "tmux", "list-panes",
                "-t", kommander.session,
                "-F", "#{pane_title}",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        titles = [t.strip() for t in result.stdout.strip().splitlines() if t.strip()]
        for agent in agents:
            assert any(
                agent in title for title in titles
            ), f"Agent '{agent}' not found in pane titles: {titles}"

    def test_pane_text_shows_agent_name(self, kommander):
        """Each pane should display the agent name (printed by the spawn script)."""
        agents = ["builder-1", "scout-1"]
        self._spawn_panes(kommander, agents)

        import time
        time.sleep(1)  # Let shells render

        for i, agent in enumerate(agents):
            text = kommander.tmux_text(pane=f"0.{i}")
            assert agent in text, (
                f"Pane 0.{i} should contain '{agent}', got:\n{text[:200]}"
            )

    def test_spawn_is_idempotent(self, kommander):
        """Calling cockpit-panes.sh twice with the same agents shouldn't duplicate panes."""
        agents = ["builder-1", "scout-1"]
        self._spawn_panes(kommander, agents)
        self._spawn_panes(kommander, agents)

        info = kommander.tmux()
        panes = info["windows"][0]["panes"]
        assert len(panes) == 2, (
            f"Duplicate spawn created extra panes: expected 2, got {len(panes)}"
        )
