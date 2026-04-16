"""Tests for Helm pure functions — group_type, build_helm_dot, build_helm_status_text, build_federation_footer.

Headless tests: no kitty, no display server, no beads CLI required.
Tests only the pure functions in helm_data.py.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from helm_data import (
    group_type,
    build_helm_dot,
    build_helm_status_text,
    build_federation_footer,
)


# ── Test data helpers ────────────────────────────────────────────────────────


def _stats(total=10, closed=5, blocked=0, wip=2, ready=None, open_n=None):
    """Create a cell_stats dict matching group_type() input shape."""
    if ready is None:
        ready = total - closed - blocked - wip
    if open_n is None:
        open_n = total - closed - blocked - wip
    return {
        "total": total,
        "closed": closed,
        "blocked": blocked,
        "wip": wip,
        "ready": ready,
        "open": open_n,
    }


def _topology_cell(name, total=10, closed=5, blocked=0, wip=2,
                   has_sub_cells=False, gates=None, sync_age_seconds=60,
                   sync_status="healthy", parent=None):
    """Create a cell dict matching get_cell_topology() output shape."""
    return {
        "name": name,
        "project_dir": f"/tmp/cells/{name}",
        "url": "",
        "stats": _stats(total=total, closed=closed, blocked=blocked, wip=wip),
        "has_sub_cells": has_sub_cells,
        "sync_age_seconds": sync_age_seconds,
        "sync_status": sync_status,
        "gates": gates or [],
        "parent": parent,
    }


def _status_cell(name, total=10, closed=5, blocked=0, wip=2,
                 has_sub_cells=False, gates=None, lead=None, agents=None):
    """Create a cell dict matching get_cell_status() output shape."""
    pct = int((closed / total) * 100) if total > 0 else 0
    if lead is None:
        lead = f"{name}-lead"
    if agents is None:
        agents = [
            {"name": f"{name}-builder-01", "role": "builder",
             "color": "#ff9e64", "status": "in_progress",
             "current_bead": "abc"},
            {"name": f"{name}-scout-01", "role": "scout",
             "color": "#7dcfff", "status": "in_progress",
             "current_bead": "def"},
        ]
    stats = _stats(total=total, closed=closed, blocked=blocked, wip=wip)
    gt = group_type(stats, has_sub_cells)
    return {
        "name": name,
        "lead": lead,
        "agents": agents,
        "progress": {"done": closed, "total": total, "pct": pct},
        "gates": gates or [],
        "group_type": gt,
    }


def _gate(gate_id, source_cell, source_bead, status="pending"):
    """Create a test gate dict."""
    return {
        "gate_id": gate_id,
        "source_cell": source_cell,
        "source_bead": source_bead,
        "status": status,
        "resolved_at": None,
    }


def _mutation(timestamp, cell_name, event_type, detail=""):
    """Create a test mutation dict."""
    return {
        "timestamp": timestamp,
        "cell": cell_name,
        "event": event_type,
        "detail": detail,
    }


# ── group_type tests ────────────────────────────────────────────────────────


def test_group_type_clowder_when_has_sub_cells():
    """Cells with sub-cells are always Clowder regardless of health."""
    stats = _stats(total=10, closed=0, blocked=8, wip=1)
    assert group_type(stats, has_sub_cells=True) == "Clowder"


def test_group_type_nuisance_when_failures():
    """Cells with some blocked issues (not majority) are Nuisance."""
    stats = _stats(total=10, closed=5, blocked=2, wip=1)
    assert group_type(stats, has_sub_cells=False) == "Nuisance"


def test_group_type_glaring_when_majority_blocked():
    """Cells where >50% of issues are blocked are Glaring."""
    stats = _stats(total=10, closed=0, blocked=6, wip=1)
    assert group_type(stats, has_sub_cells=False) == "Glaring"


def test_group_type_pounce_when_healthy():
    """Healthy cells with no blocked items and no sub-cells are Pounce."""
    stats = _stats(total=10, closed=8, blocked=0, wip=2)
    assert group_type(stats, has_sub_cells=False) == "Pounce"


# ── build_helm_dot tests ────────────────────────────────────────────────────


def test_helm_dot_returns_none_for_empty_cells():
    """No cells -> None (nothing to render)."""
    assert build_helm_dot([]) is None


def test_helm_dot_single_cell():
    """Single cell produces a valid DOT graph with one node."""
    cells = [_topology_cell("alpha")]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert "alpha" in dot
    assert "digraph" in dot


def test_helm_dot_multiple_cells_with_edges():
    """Multiple cells with parent-child relationships produce correct edges."""
    parent = _topology_cell("parent", has_sub_cells=True)
    child1 = _topology_cell("child1", parent="parent")
    child2 = _topology_cell("child2", parent="parent")
    cells = [parent, child1, child2]

    dot = build_helm_dot(cells)
    assert dot is not None
    assert '"parent" -> "child1"' in dot
    assert '"parent" -> "child2"' in dot


def test_helm_dot_uses_tokyo_night_palette():
    """All colors in the DOT output come from the Tokyo Night palette."""
    tokyo_night_colors = {
        "#1a1b26", "#a9b1d6", "#7aa2f7", "#f7768e",
        "#9ece6a", "#e0af68", "#565f89", "#24283b",
    }
    cells = [_topology_cell("test-cell", total=10, closed=5, blocked=2, wip=2)]
    dot = build_helm_dot(cells)
    assert dot is not None
    found_colors = set(re.findall(r"#[0-9a-fA-F]{6}", dot))
    for color in found_colors:
        assert color.lower() in tokyo_night_colors, (
            f"Color {color} not in Tokyo Night palette"
        )


def test_helm_dot_healthy_cell_green_border():
    """A healthy cell (all done) gets green border color."""
    cells = [_topology_cell("done-cell", total=10, closed=10, blocked=0, wip=0)]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert "#9ece6a" in dot


def test_helm_dot_blocked_cell_red_border():
    """A cell with blocked items gets red border color."""
    cells = [_topology_cell("blocked-cell", total=10, closed=0, blocked=8, wip=1)]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert "#f7768e" in dot


def test_helm_dot_wip_cell_yellow_border():
    """A cell with work in progress (no blocked) gets yellow border color."""
    cells = [_topology_cell("wip-cell", total=10, closed=2, blocked=0, wip=6)]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert "#e0af68" in dot


def test_helm_dot_shows_gate_blocker():
    """Cells with gate blockers show the gate info in the node label."""
    gate = _gate("g-1", "other-cell", "bead-42", status="pending")
    cells = [_topology_cell("gated-cell", gates=[gate])]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert "gate" in dot.lower() or "pending" in dot.lower()


def test_helm_dot_valid_syntax():
    """Output starts with 'digraph' and ends with '}'."""
    cells = [_topology_cell("alpha"), _topology_cell("beta")]
    dot = build_helm_dot(cells)
    assert dot is not None
    assert dot.strip().startswith("digraph")
    assert dot.strip().endswith("}")


# ── build_helm_status_text tests ────────────────────────────────────────────


def test_status_text_empty_cells():
    """No cells -> message saying no cells deployed."""
    text = build_helm_status_text([], [], [])
    assert text is not None
    assert "no" in text.lower() or len(text.strip()) > 0


def test_status_text_cell_card_structure():
    """Each cell gets a card with name, lead, agent roster, progress bar."""
    cells = [_status_cell("alpha", total=10, closed=5, wip=3)]
    text = build_helm_status_text(cells, [], [])
    assert "alpha" in text
    assert "alpha-lead" in text


def test_status_text_progress_bar_100_pct():
    """Complete cell shows 100% filled progress bar."""
    cells = [_status_cell("done-cell", total=10, closed=10, blocked=0, wip=0)]
    text = build_helm_status_text(cells, [], [])
    assert "100" in text


def test_status_text_progress_bar_0_pct():
    """Empty cell shows 0% progress bar."""
    cells = [_status_cell("empty-cell", total=10, closed=0, blocked=0, wip=0)]
    text = build_helm_status_text(cells, [], [])
    assert "0%" in text or "0/" in text


def test_status_text_cross_cell_gates_section():
    """Gates section shows resolved and pending gates."""
    gate_pending = _gate("g-1", "alpha", "bead-1", status="pending")
    gate_resolved = _gate("g-2", "beta", "bead-2", status="resolved")
    cells = [_status_cell("alpha")]
    text = build_helm_status_text(cells, [gate_pending, gate_resolved], [])
    assert "g-1" in text
    assert "g-2" in text


def test_status_text_mutations_section():
    """Mutations section shows recent inter-cell events."""
    mutations = [
        _mutation("2026-04-16 10:30:00", "alpha", "cell_deploy", "launched builder"),
        _mutation("2026-04-16 10:31:00", "beta", "gate_resolved", "unblocked g-1"),
    ]
    cells = [_status_cell("alpha")]
    text = build_helm_status_text(cells, [], mutations)
    assert "alpha" in text
    assert "cell_deploy" in text or "gate_resolved" in text


def test_status_text_uses_ansi_colors():
    """Output contains ANSI escape sequences for Tokyo Night colors."""
    cells = [_status_cell("alpha", total=10, closed=5, blocked=2, wip=2)]
    text = build_helm_status_text(cells, [], [])
    assert "\033[" in text


# ── build_federation_footer tests ───────────────────────────────────────────


def test_federation_footer_empty():
    """No cells -> empty or minimal footer."""
    footer = build_federation_footer([])
    assert footer is not None
    assert isinstance(footer, str)


def test_federation_footer_healthy_cells():
    """Recently synced cells show healthy indicator."""
    cells = [
        _topology_cell("alpha", sync_age_seconds=30, sync_status="healthy"),
        _topology_cell("beta", sync_age_seconds=60, sync_status="healthy"),
    ]
    footer = build_federation_footer(cells)
    # Healthy cells get green ANSI color (158;206;106 = #9ece6a)
    assert "38;2;158;206;106" in footer


def test_federation_footer_stale_cell():
    """Cell not synced in >5 minutes shows stale indicator."""
    cells = [_topology_cell("stale-cell", sync_age_seconds=600, sync_status="stale")]
    footer = build_federation_footer(cells)
    # Stale cells get yellow dot (#e0af68)
    assert "#e0af68" in footer or "stale" in footer.lower()
