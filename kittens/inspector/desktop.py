"""Desktop integration validation for the Inspector Kitten.

Checks the full install surface of kitty-kommander without launching
anything: .desktop entry, MIME association, Nautilus extension, and
CLI symlink.  Used by ``inspector desktop`` and by test_desktop.py.

One function:
    check()  -- desktop/MIME/nautilus/CLI state as structured dict
"""

import configparser
import os
import pathlib
import shutil
import subprocess


def check() -> dict:
    """Validate desktop integration artifacts.

    Inspects the .desktop file, mimeapps.list, Nautilus Python
    extension, and CLI entry point.  Never raises — returns the dict
    with ``False`` / ``None`` for missing items.

    Returns
    -------
    dict
        Structure::

            {
                "desktop_entry": { ... },
                "mime": { ... },
                "nautilus": { ... },
                "cli": { ... }
            }

        See module-level docstring or DESIGN.md for full schema.
    """
    return {
        "desktop_entry": _check_desktop_entry(),
        "mime": _check_mime(),
        "nautilus": _check_nautilus(),
        "cli": _check_cli(),
    }


# ---------------------------------------------------------------------------
# Internal checks
# ---------------------------------------------------------------------------

_DESKTOP_PATH = pathlib.Path(
    "~/.local/share/applications/kitty-kommander.desktop"
).expanduser()

_MIMEAPPS_PATH = pathlib.Path("~/.config/mimeapps.list").expanduser()

_NAUTILUS_PATH = pathlib.Path(
    "~/.local/share/nautilus-python/extensions/kitty_kommander.py"
).expanduser()


def _check_desktop_entry() -> dict:
    """Validate the .desktop file."""
    result = {
        "path": "~/.local/share/applications/kitty-kommander.desktop",
        "exists": False,
        "is_symlink": False,
        "symlink_target": None,
        "valid": False,
        "exec": None,
    }

    if not _DESKTOP_PATH.exists():
        return result

    result["exists"] = True
    result["is_symlink"] = _DESKTOP_PATH.is_symlink()
    if result["is_symlink"]:
        result["symlink_target"] = str(os.readlink(_DESKTOP_PATH))

    # Parse the Exec= line
    try:
        text = _DESKTOP_PATH.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("Exec="):
                result["exec"] = stripped[len("Exec="):]
                break
    except OSError:
        pass

    # Run desktop-file-validate if available
    validator = shutil.which("desktop-file-validate")
    if validator:
        try:
            proc = subprocess.run(
                [validator, str(_DESKTOP_PATH)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            result["valid"] = proc.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            pass
    else:
        # No validator available — trust that the file exists and has an Exec line
        result["valid"] = result["exec"] is not None

    return result


def _check_mime() -> dict:
    """Check whether mimeapps.list associates directories with kommander."""
    result = {
        "mimeapps_path": "~/.config/mimeapps.list",
        "inode_directory_includes_kommander": False,
    }

    if not _MIMEAPPS_PATH.exists():
        return result

    try:
        cp = configparser.ConfigParser(interpolation=None)
        # Preserve case of keys (MIME types are case-sensitive)
        cp.optionxform = str
        cp.read(str(_MIMEAPPS_PATH), encoding="utf-8")

        for section in cp.sections():
            inode_dir = cp.get(section, "inode/directory", fallback=None)
            if inode_dir and "kitty-kommander.desktop" in inode_dir:
                result["inode_directory_includes_kommander"] = True
                break
    except (configparser.Error, OSError):
        pass

    return result


def _check_nautilus() -> dict:
    """Validate the Nautilus Python extension."""
    result = {
        "extension_path": "~/.local/share/nautilus-python/extensions/kitty_kommander.py",
        "exists": False,
        "is_symlink": False,
        "syntax_valid": False,
    }

    if not _NAUTILUS_PATH.exists():
        return result

    result["exists"] = True
    result["is_symlink"] = _NAUTILUS_PATH.is_symlink()

    # Syntax check via compile() — do NOT import (GObject may be absent)
    try:
        source = _NAUTILUS_PATH.read_text(encoding="utf-8")
        compile(source, str(_NAUTILUS_PATH), "exec")
        result["syntax_valid"] = True
    except (SyntaxError, OSError):
        pass

    return result


def _check_cli() -> dict:
    """Validate the kitty-kommander CLI entry point."""
    result = {
        "on_path": False,
        "path": None,
        "is_symlink": False,
        "symlink_target": None,
    }

    which_path = shutil.which("kitty-kommander")
    if not which_path:
        return result

    cli = pathlib.Path(which_path)
    result["on_path"] = True
    result["path"] = str(cli)
    result["is_symlink"] = cli.is_symlink()
    if result["is_symlink"]:
        result["symlink_target"] = str(os.readlink(cli))

    return result
