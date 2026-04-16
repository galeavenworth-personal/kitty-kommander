"""Tests for build_dag_dot() — the pure DOT-generation function in dash_data."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dash_data import build_dag_dot


# ── Test data helpers ────────────────────────────────────────────────────────


def _blocked(id, title, blocked_by):
    return {"id": id, "title": title, "blocked_by": blocked_by}


def _issue(id, title=""):
    return {"id": id, "title": title}


# ── Tests ────────────────────────────────────────────────────────────────────


def test_empty_data_returns_none():
    assert build_dag_dot([], [], [], []) is None


def test_single_blocked_edge():
    blocked = [{"id": "proj-abc", "title": "blocked task", "blocked_by": ["proj-xyz"]}]
    ready = [{"id": "proj-xyz"}]
    all_open = [
        {"id": "proj-xyz", "title": "ready task"},
        {"id": "proj-abc", "title": "blocked task"},
    ]
    wip = []
    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    assert '"proj-xyz" -> "proj-abc"' in dot


@patch("dash_data.has_sprites", return_value=False)
def test_node_colors_match_state(mock_has_sprites):
    """Blocked = red, ready = green, WIP = yellow (fallback circle path)."""
    blocked = [_blocked("p-b", "blocked one", ["p-r", "p-w"])]
    ready = [_issue("p-r")]
    all_open = [
        _issue("p-r", "ready one"),
        _issue("p-b", "blocked one"),
    ]
    wip = [_issue("p-w", "wip one")]

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    # Blocked node gets red
    assert "#f7768e" in dot
    # Ready node gets green
    assert "#9ece6a" in dot
    # WIP node gets yellow
    assert "#e0af68" in dot


@patch("dash_data.has_sprites", return_value=True)
@patch("dash_data.sprite_path", return_value="/fake/yarn_ready.png")
@patch("dash_data.has_kitty_sprites", return_value=False)
def test_sprite_paths_when_available(mock_kitty, mock_sprite_path, mock_has_sprites):
    blocked = [_blocked("p-b", "task b", ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "task r"), _issue("p-b", "task b")]
    wip = []

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    assert "image=" in dot


@patch("dash_data.has_sprites", return_value=False)
@patch("dash_data.has_kitty_sprites", return_value=False)
def test_fallback_circles_when_no_sprites(mock_kitty, mock_has_sprites):
    blocked = [_blocked("p-b", "task b", ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "task r"), _issue("p-b", "task b")]
    wip = []

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    assert 'shape="circle"' in dot


def test_label_truncation():
    long_title = "A" * 60
    blocked = [_blocked("p-b", long_title, ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "ready"), _issue("p-b", long_title)]
    wip = []

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    # Title should be truncated to 32 chars in the label
    assert "A" * 33 not in dot
    assert "A" * 32 in dot


def test_dot_is_valid_syntax():
    blocked = [_blocked("p-b", "task", ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "ready"), _issue("p-b", "task")]
    wip = []

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    assert dot.startswith("digraph G {")
    assert dot.rstrip().endswith("}")


# ── Composite node tests (z0q.2) ────────────────────────────────────────────


@patch("dash_data.has_sprites", return_value=True)
@patch("dash_data.sprite_path", return_value="/fake/yarn_wip.png")
@patch("dash_data.has_kitty_sprites", return_value=True)
@patch("dash_data.kitty_sprite_path", return_value="/fake/builder_wip.png")
def test_composite_node_with_kitty_badge(mock_ksp, mock_hks, mock_sp, mock_hs):
    """When assignee_map provides an agent, the node gets a kitty badge xlabel."""
    blocked = [_blocked("p-b", "task b", ["p-w"])]
    ready = []
    all_open = [_issue("p-b", "task b")]
    wip = [_issue("p-w", "wip task")]
    assignee_map = {"p-w": "builder-01"}

    dot = build_dag_dot(blocked, ready, all_open, wip, assignee_map=assignee_map)
    assert dot is not None
    assert "xlabel=" in dot
    assert "/fake/builder_wip.png" in dot


@patch("dash_data.has_sprites", return_value=True)
@patch("dash_data.sprite_path", return_value="/fake/yarn_ready.png")
@patch("dash_data.has_kitty_sprites", return_value=False)
def test_no_kitty_badge_when_sprites_absent(mock_hks, mock_sp, mock_hs):
    """Without kitty sprites, nodes render as yarn ball only — no xlabel."""
    blocked = [_blocked("p-b", "task b", ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "ready"), _issue("p-b", "task b")]
    wip = []
    assignee_map = {"p-r": "scout-01"}

    dot = build_dag_dot(blocked, ready, all_open, wip, assignee_map=assignee_map)
    assert dot is not None
    assert "xlabel=" not in dot


# ── Bead-to-pose state mapping tests (91t.7) ───────────────────────────────


def test_bead_state_mapping():
    """kitty_sprite_path translates beads states to kitty pose names."""
    from dash_data import _BEAD_TO_POSE

    assert _BEAD_TO_POSE["wip"] == "active"
    assert _BEAD_TO_POSE["ready"] == "idle"
    assert _BEAD_TO_POSE["open"] == "idle"
    assert _BEAD_TO_POSE["blocked"] == "blocked"
    assert _BEAD_TO_POSE["done"] == "done"
    assert _BEAD_TO_POSE["in_progress"] == "active"
    assert _BEAD_TO_POSE["closed"] == "done"


@patch("dash_data.has_sprites", return_value=True)
@patch("dash_data.has_kitty_sprites", return_value=True)
def test_wip_node_gets_active_kitty_pose(mock_hks, mock_hs):
    """WIP bead state should resolve to 'active' kitty pose, not fall back to idle."""
    with patch("dash_data.sprite_path", return_value="/fake/yarn_wip.png"), \
         patch("dash_data.kitty_sprite_path", wraps=lambda role, state, size="badge":
               f"/fake/{role}_{state}.png") as mock_ksp:
        blocked = [_blocked("p-b", "task b", ["p-w"])]
        ready = []
        all_open = [_issue("p-b", "task b")]
        wip = [_issue("p-w", "wip task")]
        assignee_map = {"p-w": "builder-01"}

        dot = build_dag_dot(blocked, ready, all_open, wip, assignee_map=assignee_map)
        assert dot is not None
        # The kitty_sprite_path should be called with the bead state "wip"
        # and internally map it to "active" pose
        mock_ksp.assert_any_call("builder", "wip")
