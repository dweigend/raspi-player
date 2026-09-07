"""Expose a bounded regular-file partition to FATtools without raw-device APIs.

FATtools' macOS disk opener uses device ioctls even for files. This adapter uses
standard file I/O and enforces the selected partition's byte boundaries.
"""

import os
from pathlib import Path

from raspi_player.partitions import Partition


class ImageRegion:
    """A mutable, seekable partition stream backed exclusively by a regular file."""

    mode = "r+b"
    mbr = None

    def __init__(self, image: Path, part: Partition) -> None:
        if not image.is_file():
            raise ValueError("Image regions require a regular file.")
        self._file = image.open(self.mode)
        self.offset, self.size = part.offset, part.size
        self.seek(0)

    def seek(self, offset: int, whence: int = 0) -> int:
        bases = {0: 0, 1: self.tell(), 2: self.size}
        position = bases[whence] + offset
        if not 0 <= position <= self.size:
            raise ValueError("Filesystem access exceeds its image partition.")
        self._file.seek(self.offset + position)
        return position

    def tell(self) -> int:
        return self._file.tell() - self.offset

    def read(self, size: int = -1) -> bytearray:
        remaining = self.size - self.tell()
        return bytearray(self._file.read(remaining if size < 0 else min(size, remaining)))

    def write(self, data: bytes | bytearray | memoryview) -> int:
        if self.tell() + len(data) > self.size:
            raise ValueError("Filesystem write exceeds its image partition.")
        return self._file.write(data)

    def flush(self) -> None:
        self._file.flush()

    def close(self) -> None:
        self.flush()
        os.fsync(self._file.fileno())
        self._file.close()
