"""Pin offline input assets and image layout; no runtime network discovery."""

from pathlib import Path

BASE_URL = (
    "https://downloads.raspberrypi.com/raspios_arm64/images/"
    "raspios_arm64-2026-06-19/2026-06-18-raspios-trixie-arm64.img.xz"
)
BASE_SHA256 = "123287c05f27b0eebd8f65456f6369b8f6635fa50a3d440a4f9f6223bf58c8e2"
BASE_SIZE = 6_492_782_592
IMAGER_VERSION = "2.0.11.1"
MIB = 1024 * 1024
CHUNK_SIZE = 4 * MIB
MEDIA_RESERVE = 64 * MIB
VIDEO_SUFFIXES = {".mp4", ".mkv", ".mov", ".m4v", ".webm", ".avi", ".ts"}
PAYLOAD = Path(__file__).parent / "payload"


def offline_directory() -> Path:
    """Find adjacent assets in a portable bundle or the checkout's offline folder."""
    import sys

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve()
        if executable.parent.name == "MacOS":
            return executable.parents[3] / "offline"
        return executable.parent / "offline"
    return Path.cwd() / "offline"
