"""Validate the Pi runtime's media boundary without starting a native player."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from raspi_player.payload import play
from raspi_player.payload.play import hdmi_sink, video_path


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


def sink(name: str, card: int) -> dict[str, object]:
    """Model a PipeWire output node linked to a card's profile device."""
    return {
        "id": card + 100,
        "info": {
            "props": {
                "node.name": name,
                "media.class": "Audio/Sink",
                "device.id": card,
                "card.profile.device": 0,
            }
        },
    }


def device(card: int, available: str) -> dict[str, object]:
    """Model the availability information exported by PipeWire's ALSA device."""
    return {
        "id": card,
        "info": {
            "params": {
                "EnumRoute": [
                    {"direction": "Output", "available": available, "devices": [0]},
                ]
            }
        },
    }


def test_select_connected_hdmi_not_usb_or_disconnected_port() -> None:
    output = json.dumps(
        [
            device(1, "yes"),
            device(2, "no"),
            device(3, "yes"),
            sink("alsa_output.usb-speaker", 1),
            sink("alsa_output.hdmi0", 2),
            sink("alsa_output.hdmi1", 3),
        ]
    )
    assert hdmi_sink(output) == ("103", "alsa_output.hdmi1")


@pytest.mark.parametrize("availability", ["no", "unknown"])
def test_reject_unconnected_hdmi(availability: str) -> None:
    with pytest.raises(RuntimeError, match="No connected HDMI"):
        hdmi_sink(json.dumps([device(1, availability), sink("alsa_output.hdmi0", 1)]))


def test_audio_uses_stable_locale_and_unmutes_hdmi(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = Mock(
        return_value=subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps([device(1, "yes"), sink("alsa_output.hdmi1", 1)]),
        )
    )
    monkeypatch.setattr(play.subprocess, "run", run)
    assert play.configure_audio() == "alsa_output.hdmi1"
    assert run.call_args_list[0].kwargs["env"]["LC_ALL"] == "C"
    assert run.call_args_list[1].args[0] == [
        "wpctl",
        "set-mute",
        "101",
        "0",
    ]
    assert run.call_args_list[2].args[0] == [
        "wpctl",
        "set-volume",
        "101",
        "1.0",
    ]


@pytest.mark.parametrize("audio_available", [True, False])
def test_launch_wayland_video_even_without_hdmi_audio(
    monkeypatch: pytest.MonkeyPatch,
    audio_available: bool,
) -> None:
    monkeypatch.setattr(play, "video_path", lambda _: Path("/media/video.mp4"))
    audio = Mock(return_value="alsa_output.hdmi1")
    if not audio_available:
        audio.side_effect = RuntimeError("No connected HDMI")
    monkeypatch.setattr(play, "configure_audio", audio)
    execute = Mock()
    monkeypatch.setattr(play.os, "execve", execute)
    play.main()
    executable, args, environment = execute.call_args.args
    assert executable == "/usr/bin/cvlc"
    assert "--vout=wl-dmabuf" in args
    assert "--wl-xdg-shell" in args
    assert "--fullscreen" in args and "--repeat" in args
    assert ("--no-audio" in args) is not audio_available
    if audio_available:
        assert environment["PULSE_SINK"] == "alsa_output.hdmi1"


def test_wait_for_hdmi_handles_delayed_device_enumeration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discover = Mock(side_effect=[RuntimeError("Not ready"), ("103", "hdmi1")])
    monkeypatch.setattr(play, "discover_hdmi", discover)
    monkeypatch.setattr(play.time, "sleep", Mock())
    assert play.wait_for_hdmi() == ("103", "hdmi1")
    assert discover.call_count == 2


def test_wait_for_hdmi_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    discover = Mock(side_effect=RuntimeError("Not ready"))
    monkeypatch.setattr(play, "discover_hdmi", discover)
    monkeypatch.setattr(play.time, "sleep", Mock())
    with pytest.raises(RuntimeError, match="Not ready"):
        play.wait_for_hdmi()
    assert discover.call_count == play.AUDIO_ATTEMPTS
