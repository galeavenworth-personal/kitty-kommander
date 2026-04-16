"""Unit tests for dash_data.py — pure data functions for the cockpit dashboard.

Covers: build_sidebar_text, get_mutations, get_agents, sprite helpers, role inference.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dash_data import (
    PAL,
    ROLE_COLORS,
    _infer_role,
    _state_color,
    build_sidebar_text,
    get_mutations,
    get_agents,
    has_kitty_sprites,
    has_sprites,
    kitty_sprite_path,
    sprite_path,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _stats(total=10, closed=3, open_n=4, blocked=2, ready=3, wip=1):
    return {
        "summary": {
            "total_issues": total,
            "closed_issues": closed,
            "open_issues": open_n,
            "blocked_issues": blocked,
            "ready_issues": ready,
            "in_progress_issues": wip,
        }
    }


def _ready_issue(id, title="task", priority=2):
    return {"id": id, "title": title, "priority": priority}


# ── build_sidebar_text tests ─────────────────────────────────────────────────


class TestBuildSidebarText:
    """Tests for the pure sidebar text generator."""

    def test_basic_output_has_all_sections(self):
        text = build_sidebar_text(
            stats=_stats(),
            ready=[_ready_issue("proj-a1", "do thing")],
            commits=["abc1234 initial commit"],
        )
        assert "PROJECT HEALTH" in text
        assert "READY QUEUE" in text
        assert "RECENT MUTATIONS" in text
        assert "AGENTS" in text
        assert "RECENT COMMITS" in text

    def test_percentage_calculation(self):
        text = build_sidebar_text(
            stats=_stats(total=10, closed=5),
            ready=[], commits=[],
        )
        assert "50%" in text

    def test_zero_total_no_division_error(self):
        text = build_sidebar_text(
            stats=_stats(total=0, closed=0, open_n=0, blocked=0, ready=0, wip=0),
            ready=[], commits=[],
        )
        assert "0%" in text

    def test_empty_stats_dict(self):
        text = build_sidebar_text(stats={}, ready=[], commits=[])
        assert "PROJECT HEALTH" in text
        assert "0%" in text

    def test_ready_queue_shows_issues(self):
        issues = [
            _ready_issue("proj-x1", "fix bug", 1),
            _ready_issue("proj-x2", "add feature", 3),
        ]
        text = build_sidebar_text(stats=_stats(), ready=issues, commits=[])
        assert "x1" in text
        assert "fix bug" in text
        assert "P1" in text
        assert "P3" in text

    def test_ready_queue_truncates_at_12(self):
        issues = [_ready_issue(f"proj-i{i}", f"task {i}") for i in range(20)]
        text = build_sidebar_text(stats=_stats(), ready=issues, commits=[])
        assert "+8 more" in text

    def test_commits_section(self):
        commits = ["abc1234 feat: add dashboard", "def5678 fix: sidebar layout"]
        text = build_sidebar_text(stats=_stats(), ready=[], commits=commits)
        assert "abc1234" in text
        assert "feat: add dashboard" in text

    def test_no_commits_message(self):
        text = build_sidebar_text(stats=_stats(), ready=[], commits=[])
        assert "(no commits)" in text

    def test_mutations_section_populated(self):
        mutations = [
            {
                "timestamp": "2026-04-15 10:30:00",
                "issue_id": "proj-abc",
                "short_id": "abc",
                "old_state": "open",
                "new_state": "in_progress",
                "actor": "builder-01",
            },
        ]
        text = build_sidebar_text(
            stats=_stats(), ready=[], commits=[], mutations=mutations,
        )
        assert "abc" in text
        assert "open" in text
        assert "in_progress" in text
        assert "builder-01" in text

    def test_mutations_section_empty(self):
        text = build_sidebar_text(
            stats=_stats(), ready=[], commits=[], mutations=[],
        )
        assert "(no recent mutations)" in text

    def test_agents_section_populated(self):
        agents = [
            {
                "name": "builder-01",
                "role": "builder",
                "color": ROLE_COLORS["builder"],
                "beads": [{"id": "z0q.1", "title": "refactor data layer"}],
            },
        ]
        text = build_sidebar_text(
            stats=_stats(), ready=[], commits=[], agents=agents,
        )
        assert "builder-01" in text
        assert "z0q.1" in text
        assert "refactor data layer" in text

    def test_agents_section_empty(self):
        text = build_sidebar_text(
            stats=_stats(), ready=[], commits=[], agents=[],
        )
        assert "(no active agents)" in text

    def test_bar_width_respected(self):
        text = build_sidebar_text(
            stats=_stats(), ready=[], commits=[], bar_width=30,
        )
        # Bar width influences the separator lines
        assert "─" * 30 in text

    def test_legend_shows_all_states(self):
        text = build_sidebar_text(
            stats=_stats(closed=2, ready=3, blocked=1, wip=1, open_n=3),
            ready=[], commits=[],
        )
        assert "2 closed" in text
        assert "3 ready" in text
        assert "1 blocked" in text
        assert "1 wip" in text
        assert "3 open" in text


# ── get_mutations tests ──────────────────────────────────────────────────────


class TestGetMutations:
    """Tests for the mutations reader (reads interactions.jsonl)."""

    def test_reads_status_changes(self, tmp_path):
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        entries = [
            {
                "kind": "field_change",
                "issue_id": "proj-abc",
                "created_at": "2026-04-15T10:30:00Z",
                "actor": "builder-01",
                "extra": {"field": "status", "old_value": "open", "new_value": "in_progress"},
            },
            {
                "kind": "field_change",
                "issue_id": "proj-def",
                "created_at": "2026-04-15T11:00:00Z",
                "actor": "scout-01",
                "extra": {"field": "status", "old_value": "in_progress", "new_value": "closed"},
            },
        ]
        (beads_dir / "interactions.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )

        result = get_mutations(limit=10, project_dir=str(tmp_path))
        assert len(result) == 2
        # Most recent first
        assert result[0]["issue_id"] == "proj-def"
        assert result[0]["old_state"] == "in_progress"
        assert result[0]["new_state"] == "closed"
        assert result[0]["actor"] == "scout-01"

    def test_ignores_non_status_changes(self, tmp_path):
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        entries = [
            {
                "kind": "field_change",
                "issue_id": "proj-abc",
                "created_at": "2026-04-15T10:30:00Z",
                "actor": "user",
                "extra": {"field": "title", "old_value": "old", "new_value": "new"},
            },
            {
                "kind": "comment",
                "issue_id": "proj-abc",
                "created_at": "2026-04-15T10:31:00Z",
                "actor": "user",
                "extra": {},
            },
        ]
        (beads_dir / "interactions.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )

        result = get_mutations(limit=10, project_dir=str(tmp_path))
        assert len(result) == 0

    def test_respects_limit(self, tmp_path):
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        entries = [
            {
                "kind": "field_change",
                "issue_id": f"proj-{i}",
                "created_at": f"2026-04-15T10:{i:02d}:00Z",
                "actor": "user",
                "extra": {"field": "status", "old_value": "open", "new_value": "closed"},
            }
            for i in range(10)
        ]
        (beads_dir / "interactions.jsonl").write_text(
            "\n".join(json.dumps(e) for e in entries) + "\n"
        )

        result = get_mutations(limit=3, project_dir=str(tmp_path))
        assert len(result) == 3

    def test_missing_interactions_file(self, tmp_path):
        result = get_mutations(limit=10, project_dir=str(tmp_path))
        assert result == []

    def test_short_id_extraction(self, tmp_path):
        beads_dir = tmp_path / ".beads"
        beads_dir.mkdir()
        entry = {
            "kind": "field_change",
            "issue_id": "kitty-kommander-z0q.1",
            "created_at": "2026-04-15T10:00:00Z",
            "actor": "user",
            "extra": {"field": "status", "old_value": "open", "new_value": "in_progress"},
        }
        (beads_dir / "interactions.jsonl").write_text(json.dumps(entry) + "\n")

        result = get_mutations(limit=10, project_dir=str(tmp_path))
        assert result[0]["short_id"] == "z0q.1"


# ── get_agents tests ─────────────────────────────────────────────────────────


class TestGetAgents:
    """Tests for agent roster builder."""

    @patch("dash_data.bd")
    def test_groups_by_agent(self, mock_bd):
        mock_bd.return_value = [
            {"id": "proj-a1", "title": "task A", "assignee": "builder-01", "claimed_by": ""},
            {"id": "proj-a2", "title": "task B", "assignee": "builder-01", "claimed_by": ""},
            {"id": "proj-b1", "title": "task C", "assignee": "scout-02", "claimed_by": ""},
        ]
        result = get_agents(project_dir="/tmp/fake")
        assert len(result) == 2
        builder = next(a for a in result if a["name"] == "builder-01")
        assert len(builder["beads"]) == 2
        assert builder["role"] == "builder"

    @patch("dash_data.bd")
    def test_no_assignees_returns_empty(self, mock_bd):
        mock_bd.return_value = [
            {"id": "proj-a1", "title": "task A", "assignee": "", "claimed_by": ""},
        ]
        result = get_agents(project_dir="/tmp/fake")
        assert result == []

    @patch("dash_data.bd")
    def test_strips_email_domain(self, mock_bd):
        mock_bd.return_value = [
            {"id": "proj-a1", "title": "task", "assignee": "user@example.com", "claimed_by": ""},
        ]
        result = get_agents(project_dir="/tmp/fake")
        assert result[0]["name"] == "user"


# ── Role inference tests ─────────────────────────────────────────────────────


class TestInferRole:

    def test_builder_role(self):
        assert _infer_role("builder-01") == "builder"

    def test_scout_role(self):
        assert _infer_role("scout-alpha") == "scout"

    def test_lead_role(self):
        assert _infer_role("team-lead") == "lead"

    def test_critic_role(self):
        assert _infer_role("code-critic") == "critic"

    def test_default_role(self):
        assert _infer_role("unknown-agent") == "builder"

    def test_case_insensitive(self):
        assert _infer_role("SCOUT-01") == "scout"


# ── State color tests ────────────────────────────────────────────────────────


class TestStateColor:

    def test_blocked_returns_red(self):
        assert _state_color("blocked", "R", "G", "Y", "Gr", "F") == "R"

    def test_closed_returns_green(self):
        assert _state_color("closed", "R", "G", "Y", "Gr", "F") == "G"

    def test_in_progress_returns_yellow(self):
        assert _state_color("in_progress", "R", "G", "Y", "Gr", "F") == "Y"

    def test_open_returns_grey(self):
        assert _state_color("open", "R", "G", "Y", "Gr", "F") == "Gr"

    def test_unknown_returns_fg(self):
        assert _state_color("whatever", "R", "G", "Y", "Gr", "F") == "F"


# ── Sprite helper tests ─────────────────────────────────────────────────────


class TestSpriteHelpers:

    def test_sprite_path_existing(self, tmp_path):
        sprite_file = tmp_path / "yarn_ready.png"
        sprite_file.write_bytes(b"PNG")
        with patch("dash_data.SPRITE_DIR", tmp_path):
            result = sprite_path("ready")
            assert result == str(sprite_file)

    def test_sprite_path_missing(self, tmp_path):
        with patch("dash_data.SPRITE_DIR", tmp_path):
            result = sprite_path("ready")
            assert result is None

    def test_has_sprites_true(self, tmp_path):
        for state in ("ready", "blocked", "wip", "open"):
            (tmp_path / f"yarn_{state}.png").write_bytes(b"PNG")
        with patch("dash_data.SPRITE_DIR", tmp_path):
            assert has_sprites() is True

    def test_has_sprites_partial(self, tmp_path):
        (tmp_path / "yarn_ready.png").write_bytes(b"PNG")
        with patch("dash_data.SPRITE_DIR", tmp_path):
            assert has_sprites() is False

    def test_kitty_sprite_path_exact(self, tmp_path):
        badge_dir = tmp_path / "badge"
        badge_dir.mkdir()
        (badge_dir / "builder_wip.png").write_bytes(b"PNG")
        with patch("dash_data.KITTY_SPRITE_DIR", tmp_path):
            result = kitty_sprite_path("builder", "wip", size="badge")
            assert result is not None
            assert "builder_wip.png" in result

    def test_kitty_sprite_path_fallback_idle(self, tmp_path):
        badge_dir = tmp_path / "badge"
        badge_dir.mkdir()
        (badge_dir / "builder_idle.png").write_bytes(b"PNG")
        with patch("dash_data.KITTY_SPRITE_DIR", tmp_path):
            result = kitty_sprite_path("builder", "wip", size="badge")
            assert result is not None
            assert "builder_idle.png" in result

    def test_kitty_sprite_path_none(self, tmp_path):
        badge_dir = tmp_path / "badge"
        badge_dir.mkdir()
        with patch("dash_data.KITTY_SPRITE_DIR", tmp_path):
            result = kitty_sprite_path("builder", "wip", size="badge")
            assert result is None

    def test_has_kitty_sprites_true(self, tmp_path):
        badge_dir = tmp_path / "badge"
        badge_dir.mkdir()
        (badge_dir / "builder_idle.png").write_bytes(b"PNG")
        with patch("dash_data.KITTY_SPRITE_DIR", tmp_path):
            assert has_kitty_sprites(size="badge") is True

    def test_has_kitty_sprites_empty(self, tmp_path):
        badge_dir = tmp_path / "badge"
        badge_dir.mkdir()
        with patch("dash_data.KITTY_SPRITE_DIR", tmp_path):
            assert has_kitty_sprites(size="badge") is False
