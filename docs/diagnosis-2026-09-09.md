<!-- Independent audit of the failed physical boot and the next diagnostic build.
Records confirmed evidence and limits; does not certify successful HDMI playback. -->
# Independent boot audit — 2026-09-09

A separate agent reviewed the repository with fresh context, the mounted boot
partition and the pinned stock Linux image. It made no changes to the card.
The current installed Linux root partition could not be read from macOS.

## Confirmed gaps addressed

- Normal diagnostic services can wait for sysinit/basic/local filesystem startup.
  A 30-second timer does not bypass these dependencies. The new early checkpoint
  runs after bootfs mounts, independently of LightDM, and records pending jobs.
- The exporter previously resolved the player account before writing any report.
  A missing account could abort the whole export. It now retains system probes,
  records that error, and has a separate bounded stdout/stderr file.
- Copying over existing installation files does not repair their access modes.
  The installer now normalizes managed player configuration directories to 0755
  and files to 0644. Wrong modes on the actual card have not been demonstrated.

## Checks against the stock image

- LightDM waits for DRM devices before its pre-start hooks. Therefore the LightDM
  checkpoint alone cannot diagnose all earlier startup failures.
- The official user-configuration helper, GTK 3/Python GI, and both required Pi
  VLC Wayland plugins exist. No missing package or invalid VLC option was proved.
- The custom labwc directory must retain the distro environment. The previous
  update already copies it; its earlier omission is not a proven explanation
  for the reported black screen.
- FAT source permission bits are not inherited by Python shutil.copyfile.
- Boot PARTUUID configuration agrees with the observed partition layout.

## Evidence still needed

The maintenance log proves that the previous update finished, not that the next
normal boot completed. No periodic diagnostic report appeared after five minutes.
There is no confirmed common root cause for this absence and the black screen.

The next card boot first exports the preceding journal during maintenance, then
installs the checkpoints and reboots. A fullscreen GTK message stays mapped for
10 seconds before VLC is allowed to start. Software window mapping does not prove
physical HDMI output. Observe whether the message appears, disappears into black,
or repeats; compare this with the early, LightDM, session and player markers.

The independent follow-up found no static unit dependency cycle or staging
blocker. Linux service execution, HDMI display and sound still need the device test.

## First checkpoint device result and controlled 1080p test

The returned card provided `raspi-diagnostics.txt` after the checkpoint update.
Unlike earlier runs, this report confirms the complete software startup sequence:

- `STARTUP_SCREEN_MAPPED`, followed by `STARTUP_SCREEN_COMPLETE` ten seconds later.
- LightDM and the player service are active; both report zero restarts.
- VLC has a Wayland video framebuffer, and its two audio channels are connected
  to the HDMI sink with active streams. This does not prove visible or audible output.
- `kmsprint` reports HDMI-A-1 at **3840x2160@60.00**, pixel clock 594 MHz.
- `get_throttled` reports `0x0` at the time of collection.

The physical observation remains an invisible checkpoint, an on-monitor resolution
warning and black flicker. These results reject the hypothesis that this boot
stopped before the checkpoint. They instead prioritize display mode/signal problems.
The H.264 hardware-decoder attempt also logs an error, but VLC subsequently opens
its Wayland video output; it cannot explain the invisible GTK checkpoint before VLC.

A card-only controlled test is staged. Generic image creation defaults are unchanged
until hardware acceptance. The same HDMI-A-1 connection must be used for this test.

1. Kernel command line adds `video=HDMI-A-1:1920x1080@60`.
2. Before the original labwc autostart starts the player, it runs:
   `timeout 10 wlr-randr --output HDMI-A-1 --mode 1920x1080@60Hz --scale 1`.
   Success/failure is logged as `DISPLAY_TEST`, then a bounded `wlr-randr` query
   logs the actual output state. On failure, the checkpoint still starts, and
   no successful mode change is claimed.
3. The existing one-time maintenance mechanism installs the staged labwc files,
   retires its boot arguments and reboots. Playback, audio and logging are unchanged.

The stock image contains wlr-randr 0.4.1. Its use for labwc output management follows
[labwc's integration guide](https://labwc.github.io/integration.html#5-output-management).
Kernel mode setting and desktop settings are separate, as documented in the
[Raspberry Pi display guide](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-display-settings).

Log backup: `/private/tmp/raspi-logs-20260909-175502`.
Pre-test payload/boot backup: `/private/tmp/raspi-before-1080p-20260909-175557`.
Rollback requires restoring the backed-up autostart through maintenance and removing
only `video=HDMI-A-1:1920x1080@60` from the kernel command line. Do not restore an
old active maintenance hook accidentally. The SD card was not reformatted.

Host validation: shell/Python syntax checks and read-back equality of all changed
card files passed. Actual 1080p negotiation and physical picture still require
another device boot and its report.
