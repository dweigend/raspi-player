"""Validate and extend the pinned MBR image; never open a physical device."""

import struct
from dataclasses import dataclass
from pathlib import Path

from raspi_player.settings import MEDIA_RESERVE, MIB

SECTOR = 512
TABLE_OFFSET = 446
ENTRY = struct.Struct("<B3sB3sII")


@dataclass(frozen=True)
class Partition:
    """A validated primary partition expressed in byte offsets."""

    kind: int
    offset: int
    size: int


def read_partitions(image: Path) -> list[Partition]:
    """Read the four MBR entries and reject overlapping or out-of-file ranges."""
    with image.open("rb") as stream:
        header = stream.read(SECTOR)
    if len(header) != SECTOR or header[510:] != b"\x55\xaa":
        raise ValueError("The base image must have a valid MBR.")
    entries = [ENTRY.unpack_from(header, TABLE_OFFSET + i * 16) for i in range(4)]
    parts = [Partition(e[2], e[4] * SECTOR, e[5] * SECTOR) for e in entries]
    end = SECTOR
    for part in parts:
        if not part.size:
            continue
        if part.offset < end or part.offset + part.size > image.stat().st_size:
            raise ValueError("Invalid or overlapping image partitions.")
        end = part.offset + part.size
    return parts


def composed_size(base_size: int, video_size: int) -> int:
    """Reserve space for exFAT metadata while supporting videos larger than 4 GiB."""
    start = ((base_size + MIB - 1) // MIB) * MIB
    media_size = ((video_size + MEDIA_RESERVE + MIB - 1) // MIB) * MIB
    return start + media_size


def append_media_partition(image: Path, video_size: int) -> Partition:
    """Append one exFAT partition after an intact stock boot/root image."""
    parts = read_partitions(image)
    if [p.kind for p in parts[:2]] not in ([0x0C, 0x83], [0x0E, 0x83]):
        raise ValueError("Expected the pinned Raspberry Pi OS boot/root layout.")
    if any(p.kind or p.size for p in parts[2:]):
        raise ValueError("The source image already contains extra partitions.")
    start = ((image.stat().st_size + MIB - 1) // MIB) * MIB
    size = composed_size(image.stat().st_size, video_size) - start
    if (start + size) // SECTOR >= 2**32:
        raise ValueError("This MBR image cannot exceed 2 TiB.")
    entry = ENTRY.pack(
        0, b"\xfe\xff\xff", 7, b"\xfe\xff\xff", start // SECTOR, size // SECTOR
    )
    with image.open("r+b") as stream:
        stream.seek(TABLE_OFFSET + 2 * ENTRY.size)
        stream.write(entry)
        stream.truncate(start + size)
    return Partition(7, start, size)
