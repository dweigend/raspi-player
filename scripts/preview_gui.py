"""Show actual UI widgets with example selections for documentation captures.

No device discovery or card writing is permitted in this isolated preview.
"""

import sys
from pathlib import Path
from unittest.mock import patch

from raspi_player.gui import PlayerWindow, create_root
from raspi_player.models import Device


def preview() -> None:
    """Preview selection and the real confirmation dialog without disk access."""
    example = Device("/dev/disk-example", "Example SD card", 32_000_000_000, "example")
    with (
        patch("raspi_player.gui.list_devices", return_value=[example]),
        patch(
            "raspi_player.gui.create_card",
            side_effect=RuntimeError(
                "Documentation preview: card writing is disabled."
            ),
        ),
    ):
        root = create_root()
        window = PlayerWindow(root, Path("offline"))

        def select_example() -> None:
            if window.scanning:
                root.after(100, select_example)
                return
            window.card.current(0)
            window.video.set("/Users/example/Movies/exhibition.mp4")
            window.status.set("Choose a card.")
            if "--confirmation" in sys.argv:
                root.after(500, window.start)

        root.after(200, select_example)
        root.mainloop()


if __name__ == "__main__":
    preview()
