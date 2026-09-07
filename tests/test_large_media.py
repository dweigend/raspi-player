"""Optional full exFAT roundtrip beyond FAT32's single-file limit (about 9 GB disk)."""

import os
from pathlib import Path

import pytest
from test_images import small_image

from raspi_player.composer import add_video
from raspi_player.settings import MIB


@pytest.mark.skipif(
    os.environ.get("RASPI_PLAYER_LARGE_TEST") != "1",
    reason="Set RASPI_PLAYER_LARGE_TEST=1 for the >4 GiB roundtrip",
)
def test_video_above_four_gib(tmp_path: Path) -> None:
    image = small_image(tmp_path / "large.img")
    video = tmp_path / "large.mp4"
    with video.open("wb") as stream:
        stream.write(b"start-of-video")
        stream.seek(4 * 1024**3 + MIB)
        stream.write(b"end-of-video")
    # add_video always reopens the exFAT file and checks its complete size/hash.
    add_video(image, video, lambda _: None)
