"""Confine FATtools to ordinary image files; native Imager owns device writes."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Protocol, cast

from FATtools import Volume, mkfat

from raspi_player.image_region import ImageRegion
from raspi_player.partitions import Partition


class FatFile(Protocol):
    """Only the FATtools file-handle operations used by the composer."""

    IsValid: bool

    def read(self, size: int = -1) -> bytearray: ...
    def write(self, content: bytes | bytearray) -> None: ...
    def close(self) -> None: ...


class FatVolume(Protocol):
    """Constrain the untyped dependency at the filesystem boundary."""

    def create(self, name: str) -> FatFile: ...
    def open(self, name: str) -> FatFile: ...
    def flush(self) -> None: ...


@contextmanager
def volume(
    image: Path, part: Partition, *, format_exfat: bool = False
) -> Iterator[FatVolume]:
    """Open an explicit byte range, avoiding FATtools' logical-partition discovery."""
    if not image.is_file():
        raise ValueError("Filesystem preparation only accepts regular image files.")
    region = ImageRegion(image, part)
    root = None
    try:
        if format_exfat and mkfat.exfat_mkfs(region, part.size) != 0:
            raise ValueError("Could not format the image's media partition.")
        region.seek(0)
        root = Volume.openvolume(region)
        if isinstance(root, str):
            raise ValueError("Unrecognized filesystem in image.")
        yield cast(FatVolume, root)
    finally:
        if root is not None and not isinstance(root, str):
            root.flush()
        region.close()


def write_bytes(root: FatVolume, name: str, content: bytes) -> None:
    """Replace a file inside an already-open image filesystem."""
    handle = root.create(name)
    try:
        handle.write(content)
    finally:
        handle.close()


def read_bytes(root: FatVolume, name: str) -> bytes:
    """Read a small configuration file from an image filesystem."""
    handle = root.open(name)
    if not handle.IsValid:
        raise ValueError(f"Required image file is missing: {name}")
    try:
        return bytes(handle.read())
    finally:
        handle.close()
