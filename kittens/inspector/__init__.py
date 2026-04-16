"""Inspector Kitten — structured terminal inspection for kitty-kommander.

Kitten entry points for ``kitty +kitten inspector <subcommand>``.

Kitty calls *main()* in an overlay process and pipes its return value to
*handle_result()* in the parent kitty process.  Because the inspector is
non-interactive (no TUI), we use ``@result_handler(no_ui=True)`` and do
all real work inside *main()*, printing results directly to stdout.
"""

import glob
import json
import os
import subprocess
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_args(args):
    """Minimal arg parsing for kitten mode.

    *args* is the list of arguments **after** the kitten name, e.g. for
    ``kitty +kitten inspector ls --socket /tmp/foo`` it would be
    ``['ls', '--socket', '/tmp/foo']``.

    Returns (command, opts) where *opts* is a dict of parsed flags.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="kitty +kitten inspector")
    parser.add_argument(
        "--socket",
        default=os.environ.get("KITTY_LISTEN_ON"),
        help="Kitty control socket (default: $KITTY_LISTEN_ON)",
    )

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    # ls
    sub.add_parser("ls")

    # text
    p_text = sub.add_parser("text")
    p_text.add_argument("--match", required=True)
    p_text.add_argument("--ansi", action="store_true")

    # tmux
    p_tmux = sub.add_parser("tmux")
    p_tmux.add_argument(
        "--session",
        default=os.environ.get("KITTY_KOMMANDER_SESSION"),
    )

    # tmux-text
    p_tt = sub.add_parser("tmux-text")
    p_tt.add_argument(
        "--session",
        default=os.environ.get("KITTY_KOMMANDER_SESSION"),
    )
    p_tt.add_argument("--pane", default="0.0")

    # screenshot
    p_ss = sub.add_parser("screenshot")
    p_ss.add_argument("--tab", default=None)
    p_ss.add_argument("--pane", default=None)
    p_ss.add_argument("--output", default="screenshot.png")

    # desktop
    sub.add_parser("desktop")

    # wait
    p_wait = sub.add_parser("wait")
    p_wait.add_argument(
        "--session",
        default=os.environ.get("KITTY_KOMMANDER_SESSION"),
    )
    p_wait.add_argument("--timeout", type=int, default=30)

    # sockets
    sub.add_parser("sockets")

    return parser.parse_args(args)


def _scan_sockets():
    """Scan ``/tmp/kitty-kommander-*`` sockets and probe each one.

    Returns a list of ``{socket, responding, pid}`` dicts.
    """
    results = []
    for sock_path in sorted(glob.glob("/tmp/kitty-kommander-*")):
        entry = {"socket": sock_path, "responding": False, "pid": None}
        try:
            proc = subprocess.run(
                ["kitten", "@", "--to", f"unix:{sock_path}", "ls"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if proc.returncode == 0:
                entry["responding"] = True
                data = json.loads(proc.stdout)
                if data and isinstance(data, list):
                    # Top-level list items are OS windows; grab the first pid
                    for os_win in data:
                        for tab in os_win.get("tabs", []):
                            for window in tab.get("windows", []):
                                pid = window.get("pid")
                                if pid:
                                    entry["pid"] = pid
                                    break
                            if entry["pid"]:
                                break
                        if entry["pid"]:
                            break
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        results.append(entry)
    return results


def _dispatch(opts):
    """Dispatch parsed *opts* to the appropriate module function."""
    cmd = opts.command

    if cmd == "ls":
        try:
            from . import kitty_state
        except ImportError:
            print("error: kitty_state module not yet available", file=sys.stderr)
            sys.exit(1)
        result = kitty_state.ls(opts.socket)
        print(json.dumps(result, indent=2))

    elif cmd == "text":
        try:
            from . import kitty_state
        except ImportError:
            print("error: kitty_state module not yet available", file=sys.stderr)
            sys.exit(1)
        text = kitty_state.get_text(opts.socket, opts.match, opts.ansi)
        print(text)

    elif cmd == "tmux":
        try:
            from . import tmux_state
        except ImportError:
            print("error: tmux_state module not yet available", file=sys.stderr)
            sys.exit(1)
        result = tmux_state.session_info(opts.session)
        print(json.dumps(result, indent=2))

    elif cmd == "tmux-text":
        try:
            from . import tmux_state
        except ImportError:
            print("error: tmux_state module not yet available", file=sys.stderr)
            sys.exit(1)
        text = tmux_state.capture_pane(opts.session, opts.pane, ansi=True)
        print(text)

    elif cmd == "screenshot":
        try:
            from . import capture
        except ImportError:
            print("error: capture module not yet available", file=sys.stderr)
            sys.exit(1)
        if opts.tab or opts.pane:
            path = capture.focus_and_capture(
                opts.socket, opts.output, tab=opts.tab, pane=opts.pane,
            )
        else:
            path = capture.screenshot_focused_window(opts.output)
        print(path)

    elif cmd == "desktop":
        try:
            from . import desktop
        except ImportError:
            print("error: desktop module not yet available", file=sys.stderr)
            sys.exit(1)
        result = desktop.check()
        print(json.dumps(result, indent=2))

    elif cmd == "wait":
        try:
            from . import wait
        except ImportError:
            print("error: wait module not yet available", file=sys.stderr)
            sys.exit(1)
        ready = wait.wait_ready(opts.socket, opts.session, opts.timeout)
        sys.exit(0 if ready else 1)

    elif cmd == "sockets":
        result = _scan_sockets()
        print(json.dumps(result, indent=2))

    else:
        print(f"error: unknown command '{cmd}'", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Kitten entry points
# ---------------------------------------------------------------------------

def main(args: list) -> None:
    """Kitten main — called by kitty in the overlay process.

    *args* includes ``['inspector', ...]`` — the first element is the
    kitten name, so we strip it before parsing.
    """
    opts = _parse_args(args[1:])
    _dispatch(opts)


from kittens.tui.handler import result_handler  # noqa: E402


@result_handler(no_ui=True)
def handle_result(
    args: list,
    answer: None,
    target_window_id: int,
    boss: "Boss",
) -> None:
    """No-op result handler.

    All output is printed directly from *main()*, so there is nothing to
    relay back to the parent kitty process.
    """
    pass
