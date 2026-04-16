"""Screenshot capture for the Inspector Kitten.

Captures kitty terminal windows as PNG files using platform-native
screenshot APIs. Supports both Wayland (GNOME D-Bus) and X11
(ImageMagick ``import``) backends, detected automatically from
environment variables.

Two functions:
    screenshot_focused_window(output_path)                -- capture current window
    focus_and_capture(socket, output_path, tab, pane)     -- focus target, then capture
"""

import json
import os
import subprocess
import time


def _gnome_screenshot_window(output_path: str) -> str:
    """Capture the focused window via GNOME Shell's D-Bus screenshot API.

    Parameters
    ----------
    output_path : str
        Destination file path for the PNG screenshot.

    Returns
    -------
    str
        The output file path on success.

    Raises
    ------
    RuntimeError
        If the D-Bus call fails or the ``dbus`` module is unavailable.
    """
    try:
        import dbus
    except ImportError:
        raise RuntimeError(
            "python-dbus is not installed — required for Wayland screenshots"
        )

    bus = dbus.SessionBus()
    proxy = bus.get_object(
        "org.gnome.Shell.Screenshot",
        "/org/gnome/Shell/Screenshot",
    )
    iface = dbus.Interface(proxy, "org.gnome.Shell.Screenshot")
    success, _ = iface.ScreenshotWindow(
        False,              # include_frame
        False,              # include_cursor
        False,              # flash
        str(output_path),
    )
    if not success:
        raise RuntimeError("GNOME ScreenshotWindow D-Bus call returned failure")
    return output_path


def _get_focused_window_id(socket: str = None) -> str:
    """Get the platform window ID of the currently focused kitty window.

    Calls ``kitten @ ls`` and walks the tab/window tree to find the
    focused window's ``platform_window_id``.

    Parameters
    ----------
    socket : str, optional
        Kitty control socket path. If None, uses ``$KITTY_LISTEN_ON``.

    Returns
    -------
    str
        The platform window ID (e.g. ``"0x1234567"``).

    Raises
    ------
    RuntimeError
        If kitty is unreachable or no focused window is found.
    """
    cmd = ["kitten", "@", "ls"]
    if socket:
        cmd.extend(["--to", socket])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError(f"Cannot query kitty state: {exc}") from exc

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON from kitten @ ls: {exc}") from exc

    for os_window in raw:
        if not os_window.get("is_focused", False):
            continue
        for tab in os_window.get("tabs", []):
            if not tab.get("is_focused", False):
                continue
            for window in tab.get("windows", []):
                if not window.get("is_focused", False):
                    continue
                wid = window.get("platform_window_id")
                if wid:
                    return str(wid)

    raise RuntimeError("No focused window found in kitten @ ls output")


def _x11_screenshot_window(output_path: str, window_id: str) -> str:
    """Capture a window via ImageMagick ``import`` on X11.

    Parameters
    ----------
    output_path : str
        Destination file path for the PNG screenshot.
    window_id : str
        X11 window ID (e.g. ``"0x1234567"``).

    Returns
    -------
    str
        The output file path on success.

    Raises
    ------
    RuntimeError
        If ImageMagick ``import`` fails.
    """
    try:
        subprocess.run(
            ["import", "-window", str(window_id), str(output_path)],
            check=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ImageMagick 'import' command not found — required for X11 screenshots"
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"ImageMagick import failed: {exc}") from exc
    except subprocess.TimeoutExpired:
        raise RuntimeError("ImageMagick import timed out after 10 seconds")
    return output_path


def _portal_screenshot(output_path: str) -> str:
    """Capture the screen via XDG Desktop Portal.

    Works inside sandboxed environments (snap, flatpak) where the GNOME
    Shell D-Bus API is restricted.  Requires the user to have granted
    screenshot permission via the portal's interactive dialog at least
    once.  Subsequent non-interactive requests are auto-approved.

    Parameters
    ----------
    output_path : str
        Destination file path for the PNG screenshot.

    Returns
    -------
    str
        The output file path on success.

    Raises
    ------
    RuntimeError
        If the portal is unavailable, the user denies, or the call
        times out.
    """
    import shutil

    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib
    except ImportError:
        raise RuntimeError(
            "python-dbus and PyGObject are required for portal screenshots"
        )

    # Must create a FRESH bus connection with the GLib main loop attached.
    # If _gnome_screenshot_window was tried first, its synchronous dbus
    # connection won't have a main loop — we need a new one.
    glib_loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus(private=True, mainloop=glib_loop)
    result = [None]

    def on_response(response, results):
        if response == 0:
            uri = str(results.get("uri", ""))
            if uri.startswith("file://"):
                shutil.copy2(uri[7:], output_path)
                result[0] = output_path
        loop.quit()

    proxy = bus.get_object(
        "org.freedesktop.portal.Desktop",
        "/org/freedesktop/portal/desktop",
    )
    iface = dbus.Interface(proxy, "org.freedesktop.portal.Screenshot")
    request_path = iface.Screenshot("", {"interactive": dbus.Boolean(False)})

    bus.add_signal_receiver(
        on_response,
        signal_name="Response",
        dbus_interface="org.freedesktop.portal.Request",
        path=str(request_path),
    )

    loop = GLib.MainLoop()
    GLib.timeout_add_seconds(10, loop.quit)
    loop.run()

    if result[0] is None:
        raise RuntimeError(
            "Portal screenshot failed — permission denied or timed out. "
            "Run once with interactive=True to grant permission."
        )
    return result[0]


def screenshot_focused_window(output_path: str) -> str:
    """Capture the currently focused kitty window as a PNG screenshot.

    Platform detection (tries methods in order until one succeeds):

    1. If ``WAYLAND_DISPLAY`` is set: try GNOME D-Bus ScreenshotWindow.
    2. If step 1 fails (sandbox): fall back to XDG Desktop Portal.
    3. Elif ``DISPLAY`` is set: uses ImageMagick ``import`` with the
       window ID from ``kitten @ ls``.
    4. Otherwise: raises RuntimeError.

    Parameters
    ----------
    output_path : str
        Destination file path for the PNG screenshot.

    Returns
    -------
    str
        The output file path on success.

    Raises
    ------
    RuntimeError
        If no display server is detected or the screenshot fails.
    """
    if os.environ.get("WAYLAND_DISPLAY"):
        try:
            return _gnome_screenshot_window(output_path)
        except (RuntimeError, Exception):
            # GNOME Shell D-Bus blocked (snap/flatpak) — try portal
            return _portal_screenshot(output_path)
    elif os.environ.get("DISPLAY"):
        wid = _get_focused_window_id()
        return _x11_screenshot_window(output_path, wid)
    else:
        raise RuntimeError("No display server detected (neither WAYLAND_DISPLAY nor DISPLAY is set)")


def focus_and_capture(
    socket: str,
    output_path: str,
    tab: str = None,
    pane: str = None,
) -> str:
    """Focus a specific tab/pane in kitty, then capture a screenshot.

    Uses kitty remote control to focus the named tab and/or pane,
    waits 200ms for the window to settle, then delegates to
    :func:`screenshot_focused_window`.

    Parameters
    ----------
    socket : str
        Kitty control socket path (e.g. ``unix:/tmp/kitty-kommander-myapp``).
    output_path : str
        Destination file path for the PNG screenshot.
    tab : str, optional
        Tab title to focus (used as ``--match title:<tab>``).
    pane : str, optional
        Window/pane title to focus (used as ``--match title:<pane>``).

    Returns
    -------
    str
        The output file path on success.

    Raises
    ------
    RuntimeError
        If focusing fails or the screenshot fails.
    """
    if tab:
        try:
            subprocess.run(
                ["kitten", "@", "focus-tab", "--to", socket, "--match", f"title:{tab}"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise RuntimeError(f"Failed to focus tab '{tab}': {exc}") from exc

    if pane:
        try:
            subprocess.run(
                ["kitten", "@", "focus-window", "--to", socket, "--match", f"title:{pane}"],
                check=True,
                capture_output=True,
                timeout=10,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as exc:
            raise RuntimeError(f"Failed to focus pane '{pane}': {exc}") from exc

    # Portal-based capture needs longer settle time than direct D-Bus
    time.sleep(1.0)

    return screenshot_focused_window(output_path)
