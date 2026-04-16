"""Tests for build_dag_dot() — the pure DOT-generation function in cockpit_dash."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from cockpit_dash import build_dag_dot


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


@patch("cockpit_dash.has_sprites", return_value=False)
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


@patch("cockpit_dash.has_sprites", return_value=True)
@patch("cockpit_dash.sprite_path", return_value="/fake/yarn_ready.png")
def test_sprite_paths_when_available(mock_sprite_path, mock_has_sprites):
    blocked = [_blocked("p-b", "task b", ["p-r"])]
    ready = [_issue("p-r")]
    all_open = [_issue("p-r", "task r"), _issue("p-b", "task b")]
    wip = []

    dot = build_dag_dot(blocked, ready, all_open, wip)
    assert dot is not None
    assert "image=" in dot


@patch("cockpit_dash.has_sprites", return_value=False)
def test_fallback_circles_when_no_sprites(mock_has_sprites):
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
