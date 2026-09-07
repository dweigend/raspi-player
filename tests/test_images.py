"""Check image composition, exFAT roundtrips, and strict partition boundaries."""

import json
from pathlib import Path

import pytest

from raspi_player.boot_image import player_cmdline
from raspi_player.composer import add_video
from raspi_player.fat_image import read_bytes, volume
from raspi_player.image_region import ImageRegion
from raspi_player.partitions import (
    ENTRY,
    TABLE_OFFSET,
    Partition,
    append_media_partition,
    composed_size,
    read_partitions,
)
from raspi_player.settings import MIB


def small_image(path: Path) -> Path:
    """Create only a synthetic MBR; no native disk commands are involved."""
    header = bytearray(512)
    header[510:] = b"\x55\xaa"
    for index, part in enumerate([(12, 2048, 2048), (131, 4096, 2048)]):
        kind, start, length = part
        ENTRY.pack_into(
            header,
            TABLE_OFFSET + index * 16,
            0,
            bytes(3),
            kind,
            bytes(3),
            start,
            length,
        )
    with path.open("wb") as stream:
        stream.write(header)
        stream.truncate(3 * MIB)
    return path


def test_exfat_video_roundtrip_and_preserved_partitions(tmp_path: Path) -> None:
    image = small_image(tmp_path / "card.img")
    original = image.read_bytes()
    video = tmp_path / "video 'with spaces' ü.mp4"
    video.write_bytes(bytes(range(256)) * 30_000)
    add_video(image, video, lambda _: None)
    parts = read_partitions(image)
    assert [(p.kind, p.offset) for p in parts[:2]] == [(12, MIB), (131, 2 * MIB)]
    with image.open("rb") as source:
        source.seek(512)
        assert source.read(len(original) - 512) == original[512:]
    with volume(image, parts[2]) as root:
        assert read_bytes(root, "video.mp4") == video.read_bytes()
        assert (
            json.loads(read_bytes(root, "player.json"))["size"] == video.stat().st_size
        )


def test_large_video_layout_uses_64_bit_size(tmp_path: Path) -> None:
    image = small_image(tmp_path / "card.img")
    video_size = 5 * 1024**3
    part = append_media_partition(image, video_size)
    assert part.size > video_size
    assert image.stat().st_size == composed_size(3 * MIB, video_size)


def test_reject_existing_third_partition(tmp_path: Path) -> None:
    image = small_image(tmp_path / "card.img")
    append_media_partition(image, 100)
    with pytest.raises(ValueError, match="extra partitions"):
        append_media_partition(image, 100)


def test_region_refuses_cross_partition_writes(tmp_path: Path) -> None:
    image = tmp_path / "region.img"
    image.write_bytes(bytes(1024))
    region = ImageRegion(image, Partition(7, 512, 512))
    try:
        region.seek(510)
        with pytest.raises(ValueError, match="exceeds"):
            region.write(b"abcd")
        with pytest.raises(ValueError, match="exceeds"):
            region.seek(-1)
    finally:
        region.close()
    assert image.read_bytes() == bytes(1024)


def test_boot_disables_resize_and_keeps_root() -> None:
    original = "root=PARTUUID=abcd-02 resize quiet systemd.run=/old.sh"
    result = player_cmdline(original)
    assert "root=PARTUUID=abcd-02" in result
    assert "resize" not in result
    assert "/old.sh" not in result
    assert "cloud-init=disabled" in result
    assert player_cmdline(result) == result
