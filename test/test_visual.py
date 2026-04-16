"""Tests for screenshot capture — items 4 (timg rendering) and 5 (graphviz quality).

These tests capture PNGs but do NOT assert visual content — a Claude Code
agent reads the PNGs via the Read tool for visual review.  Tests only verify
that files are written and are non-trivially sized (> 1 KB).

Saved to test-artifacts/ (gitignored).  Requires a display server and kitty.
"""

import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

requires_kitty = pytest.mark.skipif(
    not shutil.which("kitty"), reason="kitty not installed"
)
requires_display = pytest.mark.skipif(
    not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
    reason="no display server",
)

ARTIFACTS = Path(__file__).resolve().parent.parent / "test-artifacts"


@pytest.fixture(autouse=True)
def _ensure_artifacts_dir():
    """Create the test-artifacts directory if it doesn't exist."""
    ARTIFACTS.mkdir(exist_ok=True)


@requires_kitty
@requires_display
class TestVisual:
    """Screenshot capture tests — files are written for agent visual review."""

    def test_dashboard_dag_screenshot(self, kommander):
        """Capture the Dashboard DAG pane and verify the PNG is non-trivial."""
        output = str(ARTIFACTS / "dashboard_dag.png")
        path = kommander.screenshot(output, tab="Dashboard")
        assert Path(path).exists()
        assert Path(path).stat().st_size > 1024, "Screenshot too small — likely blank"

    def test_dashboard_sidebar_screenshot(self, kommander):
        """Capture the Dashboard sidebar pane."""
        output = str(ARTIFACTS / "dashboard_sidebar.png")
        path = kommander.screenshot(output, tab="Dashboard")
        assert Path(path).exists()
        assert Path(path).stat().st_size > 1024

    def test_full_window_screenshot(self, kommander):
        """Capture the entire kitty window (no tab/pane focus)."""
        output = str(ARTIFACTS / "full_window.png")
        path = kommander.screenshot(output)
        assert Path(path).exists()
        assert Path(path).stat().st_size > 1024

    def test_screenshot_different_tabs(self, kommander):
        """Screenshots of Cockpit and Driver tabs must produce different files."""
        cockpit_png = str(ARTIFACTS / "tab_cockpit.png")
        driver_png = str(ARTIFACTS / "tab_driver.png")

        kommander.screenshot(cockpit_png, tab="Cockpit")
        kommander.screenshot(driver_png, tab="Driver")

        assert Path(cockpit_png).exists()
        assert Path(driver_png).exists()

        # Different tabs should produce different image content.
        cockpit_bytes = Path(cockpit_png).read_bytes()
        driver_bytes = Path(driver_png).read_bytes()
        assert cockpit_bytes != driver_bytes, "Cockpit and Driver screenshots are identical"
