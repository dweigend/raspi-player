<!-- Explain the operator workflow, developer entry points and evidence limits. -->
# Raspi Player

A Python desktop app that turns an SD card into an offline Raspberry Pi 5 video
player. Select a card, select a video, and create the card. Existing contents are
always erased. On first boot, the Pi configures itself, reboots automatically,
and starts fullscreen video playback on repeat.

**Status:** implemented with automated host tests. Physical SD-card writing,
first boot, and 4K playback still require the [hardware acceptance tests](docs/validation.md).
Host tests do not certify Pi playback.

## Operator workflow

1. Open **Raspi Player** from the macOS or Windows offline bundle.
2. Insert the SD card, click **Refresh cards**, and select the card.
3. Click **Choose video** and select a local video file.
4. Click **Create card** and confirm the exact card to erase.
5. Wait for preparation, writing, verification, and ejection to finish.
6. Put the card into the Pi 5, connect a monitor to HDMI0, and power it on.

No network, keyboard, login, or downloads are needed on the Pi. Allow extra time
for first-boot setup and its automatic reboot. A short pause between loops is
acceptable. The OS may request administrator access when writing the card.

On macOS, allow the system prompt for access to removable volumes so the app can
detect the SD card. Discovery runs in the background and never writes to a card.
If it times out, check for a pending macOS permission prompt, then click
**Refresh cards**. Full Disk Access is not a prerequisite. Unsigned development
rebuilds may cause macOS to request permission again.

## Run from source

Development requires [uv](https://docs.astral.sh/uv/) and Python 3.13 with Tk.

```sh
uv sync --locked
uv run raspi-player prepare-offline
uv run raspi-player
```

`prepare-offline` is the **one-time online preparation step**. It obtains the
pinned OS image and native Raspberry Pi Imager. Windows preparation downloads a
checksum-pinned Inno Setup unpacker. Finished bundles include Python and need neither developer tools
nor internet on the operator's computer.

Non-destructive developer commands:

```sh
uv run raspi-player disks
uv run raspi-player image /path/to/video.mp4 /path/to/card.img
uv run raspi-player --assets /path/to/offline
```

The `image` command creates a regular file only. Physical writing is confined to
the GUI's explicit card confirmation. Never store source files on the target card.

## Requirements and limits

- Pi 5 and an SD card with approximately 6.5 GB for the OS, plus video and metadata.
- Approximately the same free temporary space on the computer, plus offline assets.
- macOS or Windows and a writable SD reader using 512-byte sectors.
- One video; files over 4 GB use exFAT. A filename extension does not establish
  codec support. Test the real file, especially HEVC profiles and 4K frame rates.
- Media is read-only and logs use RAM. The OS root remains writable; arbitrary
  power-loss immunity is not guaranteed.
- No playlists, slideshows, streaming, web backend, or remote management.

## Development and packaging

```sh
uv run ruff check .
uv run ruff format --check .
uv run ty check --exclude src/raspi_player/payload
uv run ty check --python-platform linux src/raspi_player/payload
uv run pytest
uv build
uv run python scripts/build_app.py
```

GitHub **Checks** runs on Linux, macOS and Windows. The manually triggered
**Offline bundles** workflow produces portable native apps. Keep the application
and its adjacent `offline` directory together. Builds are unsigned/not notarized.

See [Architecture](docs/architecture.md), [Offline bundles](docs/offline-bundles.md),
[Validation](docs/validation.md), and [Third-party components](THIRD_PARTY.md).
