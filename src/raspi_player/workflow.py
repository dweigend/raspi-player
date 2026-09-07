"""Coordinate an explicit confirmed card request; preparation precedes erasure."""

import sys
import tempfile
from pathlib import Path

from raspi_player import devices
from raspi_player.composer import compose
from raspi_player.files import Progress, require_file, validate_video
from raspi_player.imager import find_imager, write_card
from raspi_player.models import WriteRequest
from raspi_player.partitions import composed_size
from raspi_player.settings import BASE_SIZE


def preflight(request: WriteRequest) -> Path:
    """Reject unsafe sources, missing assets, changed disks, and insufficient size."""
    video = validate_video(request.video)
    base = require_file(request.assets / "base.img.xz")
    imager = find_imager(request.assets)
    devices.revalidate(request.device)
    if composed_size(BASE_SIZE, video.stat().st_size) > request.device.size:
        raise ValueError("The card is too small for Raspberry Pi OS and this video.")
    for path in (
        video,
        base,
        imager,
        Path(sys.executable),
        request.workspace / "image.img",
    ):
        devices.require_other_disk(path, request.device)
    return imager


def create_card(request: WriteRequest, progress: Progress) -> None:
    """Prepare in an owned temporary directory, recheck target, then call Imager."""
    imager = preflight(request)
    with tempfile.TemporaryDirectory(
        prefix="raspi-player-", dir=request.workspace
    ) as work:
        image = compose(
            (request.assets / "base.img.xz", request.video),
            Path(work) / "card.img",
            progress,
        )
        # Preparation can take minutes: never trust the original device enumeration.
        devices.revalidate(request.device)
        write_card((imager, image), request.device, progress)
