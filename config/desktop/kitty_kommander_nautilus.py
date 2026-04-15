"""Nautilus extension: right-click a directory -> Launch kitty-kommander.

Requires: nautilus-python (dnf install nautilus-python)
Install:  symlink to ~/.local/share/nautilus-python/extensions/
Reload:   nautilus -q
"""

import subprocess
from urllib.parse import unquote

from gi.repository import GObject, Nautilus


def _launch(path):
    subprocess.Popen(
        ["kitty-kommander", path],
        start_new_session=True,
    )


class KittyKommanderExtension(GObject.GObject, Nautilus.MenuProvider):

    def get_file_items(self, files):
        if len(files) != 1 or not files[0].is_directory():
            return []
        path = unquote(files[0].get_uri().replace("file://", ""))
        item = Nautilus.MenuItem(
            name="KittyKommander::launch",
            label="Launch kitty-kommander",
            tip="Open kitty-kommander cockpit in this directory",
            icon="kitty",
        )
        item.connect("activate", lambda _m, p=path: _launch(p))
        return [item]

    def get_background_items(self, current_folder):
        if not current_folder.is_directory():
            return []
        path = unquote(current_folder.get_uri().replace("file://", ""))
        item = Nautilus.MenuItem(
            name="KittyKommander::launch_bg",
            label="Launch kitty-kommander here",
            tip="Open kitty-kommander cockpit in the current directory",
            icon="kitty",
        )
        item.connect("activate", lambda _m, p=path: _launch(p))
        return [item]
