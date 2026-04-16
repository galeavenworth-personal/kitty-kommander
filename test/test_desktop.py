"""Tests for kittens.inspector.desktop — desktop integration validation.

These tests verify that desktop.check() runs correctly and returns the
right shape.  Whether actual install artifacts exist depends on whether
install.sh has been run, so tests use conditional assertions and skips
rather than hard-failing on missing files.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import desktop.py directly to avoid kittens/inspector/__init__.py which
# requires kitty's kittens.tui.handler (unavailable outside kitty).
_desktop_path = Path(__file__).resolve().parent.parent / "kittens" / "inspector" / "desktop.py"
_spec = importlib.util.spec_from_file_location("desktop", _desktop_path)
desktop = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(desktop)


@pytest.fixture(scope="module")
def check_result():
    """Run desktop.check() once and share across all tests."""
    return desktop.check()


# -- Structural tests --------------------------------------------------------


def test_check_returns_all_sections(check_result):
    """All four top-level keys must be present."""
    assert "desktop_entry" in check_result
    assert "mime" in check_result
    assert "nautilus" in check_result
    assert "cli" in check_result


def test_check_never_raises():
    """check() must return a dict and never raise."""
    result = desktop.check()
    assert isinstance(result, dict)


# -- Desktop entry -----------------------------------------------------------


def test_desktop_entry_exists(check_result):
    """desktop_entry.exists must be bool; if symlink, target contains repo name."""
    de = check_result["desktop_entry"]
    assert isinstance(de["exists"], bool)
    if de.get("is_symlink") and de.get("symlink_target"):
        assert "kitty-kommander" in de["symlink_target"]


def test_desktop_entry_valid(check_result):
    """If the desktop entry exists, it must be valid."""
    de = check_result["desktop_entry"]
    if not de["exists"]:
        pytest.skip("desktop entry not installed")
    assert de["valid"] is True


def test_desktop_exec_correct(check_result):
    """If the desktop entry exists, its Exec line must reference kitty-kommander."""
    de = check_result["desktop_entry"]
    if not de["exists"]:
        pytest.skip("desktop entry not installed")
    assert de["exec"] is not None
    assert "kitty-kommander" in de["exec"]


# -- MIME association --------------------------------------------------------


def test_mime_association_set(check_result):
    """mime.inode_directory_includes_kommander must be bool."""
    mime = check_result["mime"]
    assert isinstance(mime["inode_directory_includes_kommander"], bool)


# -- Nautilus extension ------------------------------------------------------


def test_nautilus_extension_exists(check_result):
    """nautilus.exists must be bool."""
    assert isinstance(check_result["nautilus"]["exists"], bool)


def test_nautilus_extension_syntax(check_result):
    """If the Nautilus extension exists, it must have valid Python syntax."""
    naut = check_result["nautilus"]
    if not naut["exists"]:
        pytest.skip("nautilus extension not installed")
    assert naut["syntax_valid"] is True


# -- CLI entry point ---------------------------------------------------------


def test_cli_on_path(check_result):
    """cli.on_path must be bool."""
    assert isinstance(check_result["cli"]["on_path"], bool)


def test_cli_symlink_target(check_result):
    """If CLI is on PATH and is a symlink, its target must reference the project."""
    cli = check_result["cli"]
    if not cli["on_path"]:
        pytest.skip("kitty-kommander not on PATH")
    if not cli.get("is_symlink"):
        pytest.skip("CLI binary is not a symlink")
    target = cli.get("symlink_target", "")
    assert "kitty-kommander" in target or "launch-cockpit" in target
