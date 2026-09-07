<!-- Keep host verification distinct from physical device acceptance. -->
# Validation and troubleshooting

## Automated evidence

Tests exercise disk eligibility, internal/system-disk rejection, changed targets,
partition boundaries, preservation of existing image partitions, exFAT copy and
readback, layout sizing above 4 GiB, and failures that must never call Imager.
Runtime tests reject external paths, playlists and incomplete videos.
Automated tests never write physical disks.

## Hardware acceptance still required

- Create cards on both macOS and Windows, including cards with existing partitions.
- Verify disk selection, unplug/replug rejection, readback and safe eject.
- Boot the Pi 5 without networking. Setup and its reboot must finish without input.
- Play the real video for at least three loops and then several hours.
- Repeat with a video above 4 GiB.
- Verify actual 4K mode, hardware decoder, dropped frames, audio, temperature and
  supply stability using VLC diagnostics, `kmsprint` and `vcgencmd`.
- Kill VLC and verify restart; explicitly stop its service and verify it stays stopped.
- Test reboots, monitor power cycling, and power loss during playback.

Until these checks are recorded, playback is **not hardware validated**.

## Troubleshooting

- No card: refresh, inspect the reader's write-protect switch. Unknown/virtual
  devices and non-512-byte sectors are rejected.
- Missing assets: run `prepare-offline` online or restore the adjacent `offline` folder.
- Not enough space: free host temporary space or choose a larger card.
- Imager failure: the card is not ready. Reconnect and create it again; do not disable verification.
- First-boot failure: read the Pi boot console. Correct the setup and recreate the card.
- Playback failure: in a maintenance console inside the player session, inspect
  `journalctl --user -u raspi-player.service`. SSH is not preconfigured.
- 4K stutter: check the original codec/profile, active cooling, power supply,
  HDMI mode and decoder. Automatic transcoding is not implemented.
