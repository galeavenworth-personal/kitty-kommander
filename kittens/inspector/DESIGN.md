# kitten inspector — Design

Terminal integration testing for kitty-kommander. A capture and inspection
tool that makes the previously untestable testable.

## Problem

Eight aspects of kitty-kommander were flagged as untestable:

1. Kitty session file actually producing four tabs with correct layout
2. tmux session creation/attachment via the `sh -c` wrapper
3. `$KITTY_KOMMANDER_SESSION` env var expansion inside kitty's session file parser
4. timg inline image rendering in kitty's graphics protocol
5. Graphviz visual output quality (correct colors, positioning)
6. Desktop entry MIME association / Nautilus extension loading
7. The actual "right-click → Launch kitty-kommander" UX flow
8. Socket binding conflicts between parallel instances

## Solution

A custom kitty kitten that provides structured inspection (JSON) and
screenshot capture (PNG). The kitten is a camera and a tape measure —
the AI is whoever is running Claude Code and reading the output.

**The kitten does NOT contain AI.** A Claude Code agent (the operator,
or a teammate) uses the kitten's output and the Read tool to inspect
screenshots visually.

## Architecture

```
kittens/inspector/
    __init__.py          kitten entry points (main + handle_result)
    __main__.py          standalone CLI (python -m kittens.inspector)
    kitty_state.py       kitten @ ls, get-text wrappers
    tmux_state.py        tmux list-*, capture-pane wrappers
    capture.py           screenshot via GNOME D-Bus / X11 fallback
    desktop.py           desktop entry + MIME + nautilus validation
    wait.py              poll-until-ready with timeout
```

### Invocation modes

| Mode | Command | When |
|------|---------|------|
| As kitten | `kitty +kitten inspector ls` | Inside a running kitty |
| As CLI | `python -m kittens.inspector --socket <path> ls` | From test runner, CI, another terminal |

Both modes use the same underlying functions. The kitten mode gets the
socket from `$KITTY_LISTEN_ON`. The CLI mode takes `--socket` explicitly.

### Dependencies

**Zero pip installs.** Python stdlib + system tools already present:

| Need | Source |
|------|--------|
| `kitten @` remote control | kitty (installed) |
| `tmux` CLI | tmux (installed) |
| `dbus` module | python-dbus (installed on Fedora) |
| `subprocess`, `json`, `socket`, `pathlib`, `time` | Python stdlib |
| `import` (ImageMagick) | X11 fallback (installed) |

## Subcommands

### `inspector ls`

Query kitty tab/window/pane tree via `kitten @ ls`.

```
inspector ls [--socket PATH]
```

Returns:
```json
{
  "tabs": [
    {
      "index": 0,
      "title": "Cockpit",
      "layout": "tall",
      "is_focused": false,
      "windows": [
        {"title": "tmux", "pid": 12345, "cwd": "/home/user/project"}
      ]
    },
    ...
  ]
}
```

**Covers items**: 1 (tab count, titles, layout), 3 (env var — tab structure
proves session file parsed correctly).

### `inspector text`

Read screen content from a kitty window via `kitten @ get-text`.

```
inspector text [--socket PATH] --match "title:Dashboard" [--ansi]
```

Returns plain text or ANSI-formatted text content.

**Covers items**: 1 (verify process running in each tab), 2 (verify tmux
pane content).

### `inspector tmux`

Query tmux session/window/pane structure.

```
inspector tmux [--session NAME]
```

Returns:
```json
{
  "session": "cockpit-myapp",
  "exists": true,
  "windows": [
    {
      "index": 0,
      "name": "bash",
      "panes": [
        {"index": 0, "command": "bash", "pid": 12346, "size": "213x48"}
      ]
    }
  ]
}
```

**Covers items**: 2 (tmux session created correctly), 3 (session name
matches expected slug — the name IS the proof that env var expanded).

### `inspector tmux-text`

Capture text content of a tmux pane via `tmux capture-pane -p -e`.

```
inspector tmux-text [--session NAME] [--pane INDEX]
```

Returns ANSI text content.

### `inspector screenshot`

Capture the kitty window as PNG.

```
inspector screenshot [--socket PATH] [--tab TITLE] [--pane TITLE] [--output PATH]
```

Sequence:
1. Focus target tab via `kitten @ focus-tab --match title:<tab>`
2. Focus target pane via `kitten @ focus-window --match title:<pane>`
3. 200ms settle delay
4. Platform screenshot:
   - Wayland + GNOME: `org.gnome.Shell.Screenshot.ScreenshotWindow` via D-Bus
   - X11: `import -window <wid>` via ImageMagick (wid from `kitten @ ls`)
5. Return PNG file path

**Covers items**: 4 (timg image rendering — agent reads the PNG),
5 (graphviz visual quality — agent inspects colors/layout).

### `inspector desktop`

Validate desktop integration without launching anything.

```
inspector desktop
```

Returns:
```json
{
  "desktop_entry": {
    "path": "~/.local/share/applications/kitty-kommander.desktop",
    "exists": true,
    "is_symlink": true,
    "symlink_target": "/home/user/Projects/kitty-kommander/config/desktop/kitty-kommander.desktop",
    "valid": true,
    "exec": "kitty-kommander %f"
  },
  "mime": {
    "mimeapps_path": "~/.config/mimeapps.list",
    "inode_directory_includes_kommander": true
  },
  "nautilus": {
    "extension_path": "~/.local/share/nautilus-python/extensions/kitty_kommander.py",
    "exists": true,
    "is_symlink": true,
    "syntax_valid": true
  },
  "cli": {
    "on_path": true,
    "path": "/home/user/.local/bin/kitty-kommander",
    "is_symlink": true,
    "symlink_target": "/home/user/Projects/kitty-kommander/scripts/launch-cockpit.sh"
  }
}
```

Checks performed:
- `desktop-file-validate` on the .desktop file (if available)
- Symlink chain validation (readlink → verify points to repo)
- `grep kitty-kommander` in mimeapps.list
- Python syntax check on nautilus extension (compile, don't import)
- `which kitty-kommander` + readlink for CLI entry point

**Covers item**: 6 (desktop/MIME/nautilus — validates full install surface).

### `inspector wait`

Block until a kitty-kommander instance is fully ready.

```
inspector wait [--socket PATH] [--session NAME] [--timeout SEC]
```

Readiness phases (all must pass):
1. Socket accepts connections
2. `kitten @ ls` returns 4 tabs
3. `tmux has-session -t <session>` succeeds
4. Dashboard pane has content (text length > threshold)

Exit 0 on ready, exit 1 on timeout.

**Covers items**: Test reliability for all items. Without this, tests
are races against startup time.

### `inspector sockets`

List all kitty-kommander sockets and their status.

```
inspector sockets
```

Returns:
```json
[
  {"socket": "/tmp/kitty-kommander-alpha", "responding": true, "pid": 11111},
  {"socket": "/tmp/kitty-kommander-beta", "responding": true, "pid": 22222}
]
```

Scans `/tmp/kitty-kommander-*` sockets, attempts `kitten @ ls` on each.

**Covers item**: 8 (parallel socket conflicts — verify independent instances).

## Coverage map

| # | Previously untestable item | Method | Deterministic? |
|---|---------------------------|--------|----------------|
| 1 | Session file → 4 tabs | `inspector ls` JSON | Yes |
| 2 | tmux session via `sh -c` | `inspector tmux` JSON | Yes |
| 3 | Env var expansion | tmux session name = proof | Yes |
| 4 | timg inline images | `inspector screenshot` + agent reads PNG | No (AI vision) |
| 5 | Graphviz visual quality | screenshot + agent + DOT unit tests | Partial |
| 6 | Desktop/MIME/Nautilus | `inspector desktop` JSON | Yes |
| 7 | Right-click UX flow | `kitty-kommander <dir>` + `inspector wait` | Yes (minus GUI trigger) |
| 8 | Parallel socket conflicts | Two instances + `inspector sockets` | Yes |

6 of 8 become fully deterministic. 2 require screenshot + agent vision.

## Test organization

```
test/
    conftest.py            pytest fixture: launch, wait, inspect, cleanup
    test_structure.py      items 1, 2, 3 — tab layout, tmux session, env var
    test_parallel.py       item 8 — two instances, independent sockets/sessions
    test_desktop.py        item 6 — desktop entry, MIME, symlinks (no launch needed)
    test_visual.py         items 4, 5 — screenshot capture (agent reviews PNGs)
    test_dag_dot.py        item 5 complement — DOT string assertions (deterministic)
```

### conftest.py fixture

```python
@pytest.fixture
def kommander(tmp_path):
    """Launch a kitty-kommander instance on a temp project dir."""
    # Init beads in temp dir so dashboard has something to show
    subprocess.run(["bd", "init"], cwd=tmp_path)

    proc = subprocess.Popen(["kitty-kommander", str(tmp_path)])
    socket = f"unix:/tmp/kitty-kommander-{tmp_path.name}"
    session = f"cockpit-{tmp_path.name}"

    # Block until ready
    inspector.wait(socket=socket, session=session, timeout=20)

    yield InspectorHandle(proc=proc, socket=socket, session=session, dir=tmp_path)

    # Cleanup
    proc.terminate()
    proc.wait(timeout=5)
    subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
```

## Complementary refactor: cockpit_dash.py

To make item 5 (graphviz quality) partially deterministic, extract the DOT
generation into a pure function:

```python
# Before (render_dag does everything):
def render_dag():
    blocked = bd(["blocked"])
    ...
    dot_str = "\n".join(dot)
    # pipes to graphviz and timg

# After (separate concerns):
def build_dag_dot(blocked, ready, all_open, wip):
    """Pure function: bd data → DOT string. No I/O."""
    ...
    return "\n".join(dot)

def render_dag():
    blocked = bd(["blocked"])
    ...
    dot_str = build_dag_dot(blocked, ready, all_open, wip)
    # pipes to graphviz and timg
```

Then `test_dag_dot.py` tests the DOT string directly with mock bd data:
correct node colors, edge relationships, sprite paths, label formatting.

## Screenshot capture internals

### GNOME D-Bus (Wayland — primary path)

```python
import dbus

def gnome_screenshot_window(output_path):
    bus = dbus.SessionBus()
    proxy = bus.get_object(
        "org.gnome.Shell.Screenshot",
        "/org/gnome/Shell/Screenshot"
    )
    iface = dbus.Interface(proxy, "org.gnome.Shell.Screenshot")
    success, _ = iface.ScreenshotWindow(
        False,   # include_frame
        False,   # include_cursor
        False,   # flash
        str(output_path)
    )
    if not success:
        raise RuntimeError("GNOME ScreenshotWindow failed")
    return output_path
```

### X11 fallback

```python
def x11_screenshot_window(output_path, window_id):
    subprocess.run(
        ["import", "-window", str(window_id), str(output_path)],
        check=True, timeout=10
    )
    return output_path
```

Window ID sourced from `kitten @ ls` JSON (`platform_window_id` field).

### Platform detection

```python
def screenshot_focused_window(output_path):
    if os.environ.get("WAYLAND_DISPLAY"):
        return gnome_screenshot_window(output_path)
    elif os.environ.get("DISPLAY"):
        wid = get_focused_window_id()  # from kitten @ ls
        return x11_screenshot_window(output_path, wid)
    else:
        raise RuntimeError("No display server detected")
```

## Install integration

`install.sh` addition:

```bash
# Symlink inspector kitten
KITTEN_DIR="$HOME/.config/kitty"
symlink "$SCRIPT_DIR/kittens/inspector" "$KITTEN_DIR/inspector"
```

This makes `kitty +kitten inspector <subcommand>` work from any kitty window.

## What remains untestable

One item: **"Does the right-click menu item appear in Nautilus's GUI?"**
This requires desktop GUI automation (dogtail/LDTP). The user has
volunteered to handle this manually.

Everything else — from session file parsing to parallel instance
isolation to inline image rendering — becomes inspectable.
