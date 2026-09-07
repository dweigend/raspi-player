"""Validate the Pi runtime's media boundary without starting a native player."""

import json
from pathlib import Path

import pytest

from raspi_player.payload.play import video_path


@pytest.mark.parametrize(
    "name", ["../video.mp4", "/tmp/video.mp4", "http://host/video.mp4", "playlist.m3u"]
)
def test_reject_nonlocal_video(tmp_path: Path, name: str) -> None:
    (tmp_path / "player.json").write_text(json.dumps({"file": name, "size": 10}))
    with pytest.raises(ValueError):
        video_path(tmp_path)


def test_reject_incomplete_video(tmp_path: Path) -> None:
    (tmp_path / "video.mp4").write_bytes(b"partial")
    (tmp_path / "player.json").write_text(
        json.dumps({"file": "video.mp4", "size": 100})
    )
    with pytest.raises(ValueError, match="incomplete"):
        video_path(tmp_path)


def test_accept_complete_video(tmp_path: Path) -> None:
    video = tmp_path / "video.mp4"
    video.write_bytes(b"video")
    (tmp_path / "player.json").write_text(json.dumps({"file": video.name, "size": 5}))
    assert video_path(tmp_path) == video
