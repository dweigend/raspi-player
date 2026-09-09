"""Validate one local video and replace this process with the native VLC player.

Runs without root in the kiosk session. systemd owns retries and lifecycle;
Audio discovery is bounded at startup; this script never renders or writes media.
"""

import json
import os
import subprocess
import time
from pathlib import Path

MEDIA = Path("/srv/raspi-player")
AUDIO_ATTEMPTS = 10
AUDIO_RETRY_SECONDS = 0.5


def hdmi_sink(output: str) -> tuple[str, str]:
    """Select a connected HDMI sink, never an unrelated USB/Bluetooth output."""
    objects = json.loads(output)
    connected = connected_routes(objects)
    for node in objects:
        props = node.get("info", {}).get("props", {})
        name = props.get("node.name", "")
        if props.get("media.class") != "Audio/Sink" or "hdmi" not in name.lower():
            continue
        route = (str(props.get("device.id")), int(props.get("card.profile.device", -1)))
        if route in connected:
            return str(node["id"]), name
    raise RuntimeError("No connected HDMI audio output is available.")


def connected_routes(objects: list[dict]) -> set[tuple[str, int]]:
    """Resolve available output routes to their PipeWire device/profile IDs."""
    connected: set[tuple[str, int]] = set()
    for device in objects:
        routes = device.get("info", {}).get("params", {}).get("EnumRoute", [])
        for route in routes:
            if route.get("direction") != "Output" or route.get("available") != "yes":
                continue
            for profile_device in route.get("devices", []):
                connected.add((str(device["id"]), profile_device))
    return connected


def discover_hdmi() -> tuple[str, str]:
    """Read the current audio graph without depending on localized CLI tables."""
    result = subprocess.run(
        ["pw-dump"],
        check=True,
        capture_output=True,
        text=True,
        timeout=2,
        env={**os.environ, "LC_ALL": "C"},
    )
    return hdmi_sink(result.stdout)


def wait_for_hdmi() -> tuple[str, str]:
    """Allow WirePlumber to enumerate outputs after its service has started."""
    for attempt in range(AUDIO_ATTEMPTS):
        try:
            return discover_hdmi()
        except (RuntimeError, subprocess.SubprocessError):
            if attempt == AUDIO_ATTEMPTS - 1:
                raise
            time.sleep(AUDIO_RETRY_SECONDS)
    raise RuntimeError("HDMI discovery did not complete.")


def configure_audio() -> str:
    """Use installed PipeWire tools to select and unmute HDMI PCM audio."""
    node_id, name = wait_for_hdmi()
    for command, value in (("set-mute", "0"), ("set-volume", "1.0")):
        subprocess.run(["wpctl", command, node_id, value], check=True, timeout=10)
    return name


def video_path(directory: Path) -> Path:
    """Reject playlists, external paths, symlinks and incomplete local media."""
    metadata = json.loads((directory / "player.json").read_text())
    name = metadata["file"]
    if (
        not isinstance(name, str)
        or Path(name).name != name
        or not name.startswith("video.")
    ):
        raise ValueError("Invalid local video name.")
    path = directory / name
    if (
        path.is_symlink()
        or not path.is_file()
        or path.stat().st_size != metadata["size"]
    ):
        raise ValueError("Video is missing or incomplete.")
    return path


def player_arguments(path: Path) -> list[str]:
    """Use the Pi OS Wayland plugins; labwc owns the monitor's native mode."""
    return [
        "/usr/bin/cvlc",
        "--ignore-config",
        "--intf=dummy",
        "--vout=wl-dmabuf",
        "--wl-xdg-shell",
        "--aout=pulse",
        "--fullscreen",
        "--repeat",
        "--play-and-exit",
        "--no-video-title-show",
        "--no-osd",
        "--no-video-deco",
        "--no-embedded-video",
        "--no-metadata-network-access",
        "--no-media-library",
        "--no-one-instance",
        "--mouse-hide-timeout=0",
        "--no-spu",
        str(path),
    ]


def main() -> None:
    path = video_path(MEDIA)
    environment = os.environ.copy()
    args = player_arguments(path)
    try:
        environment["PULSE_SINK"] = configure_audio()
        print(f"HDMI audio: {environment['PULSE_SINK']}", flush=True)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        # An absent audio device must not turn a working video into a black screen.
        print(f"HDMI audio unavailable; playing without sound: {error}", flush=True)
        args.insert(1, "--no-audio")
    print(f"Playing {path} via the Pi Wayland output", flush=True)
    os.execve(args[0], args, environment)


if __name__ == "__main__":
    main()
