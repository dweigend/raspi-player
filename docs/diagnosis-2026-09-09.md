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
