"""Show a visible startup checkpoint before systemd is allowed to launch VLC.

Uses GTK already installed in the Pi OS image. A mapped window starts the delay;
failure or premature closure returns an error. Mapping is not proof of HDMI output.
"""

import os
from typing import Any

DISPLAY_SECONDS = 10


class StartupScreen:
    """Own one short-lived fullscreen window, without supervising the video."""

    def __init__(self, gtk: Any, glib: Any) -> None:
        self.gtk = gtk
        self.glib = glib
        self.mapped = False
        self.completed = False
        self.window = gtk.Window(title="Raspi Player")
        self.window.set_deletable(False)
        self.window.connect("map-event", self.on_map)
        self.window.connect("destroy", lambda *_: gtk.main_quit())
        self.add_content()

    def add_content(self) -> None:
        label = self.gtk.Label()
        label.set_markup(
            '<span size="48000" weight="bold">Player wird gestartet</span>'
            '\n\n<span size="24000">VLC startet gleich …</span>'
        )
        label.set_justify(self.gtk.Justification.CENTER)
        self.window.add(label)
        self.window.fullscreen()

    def on_map(self, _widget: Any, _event: Any) -> bool:
        if not self.mapped:
            self.mapped = True
            print("STARTUP_SCREEN_MAPPED: waiting 10 seconds before VLC", flush=True)
            self.glib.timeout_add_seconds(DISPLAY_SECONDS, self.finish)
        return False

    def finish(self) -> bool:
        self.completed = True
        print("STARTUP_SCREEN_COMPLETE: permitting VLC start", flush=True)
        self.gtk.main_quit()
        return False

    def run(self) -> None:
        self.window.show_all()
        self.gtk.main()
        if not self.completed:
            raise RuntimeError(
                "Startup screen ended before the visible checkpoint completed."
            )


def main() -> None:
    print("STARTUP_SCREEN_BEGIN: opening native Wayland window", flush=True)
    os.environ["GDK_BACKEND"] = "wayland"
    import gi  # ty: ignore[unresolved-import]  # Provided by the Pi OS image.

    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib, Gtk  # ty: ignore[unresolved-import]

    ready, _ = Gtk.init_check([])
    if not ready:
        raise RuntimeError(
            "Cannot connect the startup screen to the graphical session."
        )
    StartupScreen(Gtk, GLib).run()


if __name__ == "__main__":
    main()
