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

### Always-on diagnostics

The visible startup sequence is: boot, graphical session, fullscreen
"Player wird gestartet" for ten seconds, then VLC. If that screen never appears,
VLC has not passed its startup checkpoint. If it appears and then video fails,
inspect the player and audio logs next. A repeated screen may indicate service
retries, not successful playback.

`raspi-early-boot.txt` is written after bootfs mounts, independently of normal
service startup and LightDM. It records pending systemd jobs. If this file is
missing, investigate the bootfs mount and earlier boot stages.

`raspi-boot.txt` is written directly before LightDM starts; it does not depend on
the periodic diagnostic timer. It retains the prior report as
`raspi-boot-previous.txt`. `raspi-diagnostic-service.txt` contains the latest
exporter's own stdout/stderr, including any traceback. These distinguish failure
before graphical startup from a failure inside the logging service.

Logging can stay enabled after playback works. The first setup writes
`raspi-setup.txt` on the boot partition, including Python exceptions. After a
normal boot, `raspi-diagnostics.txt` appears after the 30-second timer and normal
service dependencies are ready, and
is refreshed every five minutes; `raspi-diagnostics-previous.txt` retains the
preceding report. Each report is capped at 128 KiB. Insert the card into a Mac
to read these files on `bootfs` without mounting the Linux partition.

The reports distinguish repeated player exits, compositor/session failures,
disconnected HDMI connectors, the current display mode and missing audio routes.
Native journals retain more detail across reboots with a 32 MiB storage budget.
An abrupt power cut can lose recent buffered messages; allow at least one minute
after a failed boot before collecting the card. No remote login is enabled.

The missing stock labwc environment was confirmed by inspecting the pinned OS
image. Preserving it fixes a configuration omission; confirmation that it resolves
the reported black screen and flicker still requires the device logs and a boot test.

### Common failures

- No card: refresh, inspect the reader's write-protect switch. Unknown/virtual
  devices and non-512-byte sectors are rejected.
- Missing assets: on macOS, copy the complete app from the DMG into Applications
  again; its offline assets are inside the app. On Windows, restore the complete
  portable folder including its adjacent `offline` directory. When running from
  source, run `prepare-offline` online.
- Not enough space: free host temporary space or choose a larger card.
- Imager failure: the card is not ready. Reconnect and create it again; do not disable verification.
- First-boot failure: read the Pi boot console. Correct the setup and recreate the card.
- Playback failure: in a maintenance console inside the player session, inspect
  `journalctl --user -u raspi-player.service`. SSH is not preconfigured.
- Black screen after boot: successful card writing proves image transfer, not
  playback. Collect `journalctl --user -u raspi-player.service -b --no-pager`,
  `systemctl --user status raspi-player.service`, and the LightDM session log
  before attributing the failure to the display or codec. Explicit Pi Wayland
  output and HDMI sound were confirmed on the tested Pi 5/LG setup at 1080p60.
- HDMI sound: connect and power on the monitor before boot. `pw-dump` and
  `wpctl status -n` show the available devices. The service logs the chosen HDMI
  sink or the reason it started without audio. Turn up the monitor's own volume.
  A monitor that exposes no available HDMI audio route is treated as video-only.
  If audio becomes available after startup, restart the player service or reboot.
- A 4K monitor does not require a 4K source file: the reported test video is
  1920x1080 H.264 at 25 fps with AAC audio. Fullscreen scales it to the active
  display mode. Check `kmsprint` on the Pi to confirm the actual negotiated mode;
  HDMI0 is configured for 1920x1080 at 60 Hz in both boot and graphical startup.
- 4K stutter: check the original codec/profile, active cooling, power supply,
  HDMI mode and decoder. Automatic transcoding is not implemented.
