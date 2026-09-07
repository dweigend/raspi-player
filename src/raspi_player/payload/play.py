"""Validate one local video and replace this process with the native VLC player.

Runs without root in the kiosk session. systemd owns retries and lifecycle;
this script does not render, poll, download, or write media.
"""

import json
import os
from pathlib import Path

MEDIA = Path("/srv/raspi-player")


def video_path(directory: Path) -> Path:
    """Reject playlists, external paths, symlinks and incomplete local media."""
    metadata = json.loads((directory / "player.json").read_text())
    name = metadata["file"]
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or not name.startswith("video.")
    ):
        raise ValueError("Invalid local video name.")
    path = directory / name
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != metadata["size"]
    ):
        raise ValueError("Video is missing or incomplete.")
    return path


def main() -> None:
    path = video_path(MEDIA)
    args = [
        "/usr/bin/cvlc",
        "--ignore-config",
        "--intf=dummy",
        "--fullscreen",
        "--repeat",
        "--play-and-exit",
        "--no-video-title-show",
        "--no-osd",
        "--no-video-deco",
        "--no-embedded-video",
        "--no-metadata-network-access",
        "--no-media-library",
        "--no-one-instance",
        "--mouse-hide-timeout=0",
        "--no-spu",
        str(path),
    ]
    os.execv(args[0], args)


if __name__ == "__main__":
    main()
