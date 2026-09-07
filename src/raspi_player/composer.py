"""Compose and verify a complete video-specific image before touching a card."""

import hashlib
import json
import lzma
import os
import shutil
from pathlib import Path

from raspi_player.boot_image import configure_boot
from raspi_player.fat_image import volume, write_bytes
from raspi_player.files import (
    Progress,
    copy_stream,
    require_file,
    sha256,
    validate_video,
)
from raspi_player.partitions import Partition, append_media_partition, composed_size
from raspi_player.settings import BASE_SHA256, BASE_SIZE, CHUNK_SIZE, MIB


def unpack_base(source: Path, output: Path, progress: Progress) -> None:
    """Require the exact upstream image checksum before extraction."""
    progress("Checking the offline Raspberry Pi OS image…")
    if sha256(require_file(source)) != BASE_SHA256:
        raise ValueError("Base-image checksum mismatch. Run prepare-offline again.")
    with lzma.open(source, "rb") as reader, output.open("xb") as writer:
        copy_stream(reader, writer, progress)
        writer.flush()
        os.fsync(writer.fileno())
    if output.stat().st_size != BASE_SIZE:
        raise ValueError("Unexpected uncompressed Raspberry Pi OS image size.")


def add_video(image: Path, video: Path, progress: Progress) -> None:
    """Create exFAT, copy the video and compare a separate filesystem readback."""
    part = append_media_partition(image, video.stat().st_size)
    name = "video" + video.suffix.lower()
    before = video.stat()
    with volume(image, part, format_exfat=True) as root:
        target = root.create(name)
        try:
            with video.open("rb") as source:
                digest = copy_stream(source, target, progress)
        finally:
            target.close()
        metadata = {"file": name, "size": before.st_size, "sha256": digest}
        write_bytes(root, "player.json", json.dumps(metadata).encode())
    after = video.stat()
    if (after.st_size, after.st_mtime_ns, after.st_ino) != (
        before.st_size,
        before.st_mtime_ns,
        before.st_ino,
    ):
        raise ValueError("The source video changed while being copied.")
    progress("Verifying the video inside the prepared image…")
    verify_video(image, part, metadata)


def verify_video(image: Path, part: Partition, metadata: dict[str, str | int]) -> None:
    """Reopen exFAT and verify content independently of the write handle."""
    with volume(image, part) as root:
        source = root.open(str(metadata["file"]))
        digest = hashlib.sha256()
        size = 0
        try:
            while block := source.read(CHUNK_SIZE):
                digest.update(block)
                size += len(block)
        finally:
            source.close()
    if size != metadata["size"] or digest.hexdigest() != metadata["sha256"]:
        raise ValueError("The video failed image readback verification.")


def compose(inputs: tuple[Path, Path], output: Path, progress: Progress) -> Path:
    """Build a new image from a base archive and video; refuse existing outputs."""
    base, video = inputs[0], validate_video(inputs[1])
    if output.exists():
        raise ValueError("Refusing to overwrite an existing output image.")
    required = composed_size(BASE_SIZE, video.stat().st_size) + 256 * MIB
    if shutil.disk_usage(output.parent).free < required:
        raise ValueError(
            f"At least {required / (1024**3):.1f} GiB free space is needed."
        )
    unpack_base(base, output, progress)
    configure_boot(output)
    add_video(output, video, progress)
    progress("Complete image prepared and video verified.")
    return output
