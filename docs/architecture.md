<!-- Document the implemented owners, card layout and lifecycle. -->
# Architecture

Tkinter owns card/video selection and confirmation. A worker runs the workflow;
a queue marshals status back to the Tk thread. Native structured APIs enumerate
physical whole disks: macOS `diskutil -plist`, Windows PowerShell `Get-Disk`.
The workflow checks eligibility, identity, capacity and source-disk separation.

The composer only opens regular files. It verifies and extracts the pinned OS,
edits the boot FAT32 using pyfatfs, appends exFAT using FATtools, copies the video,
and verifies it by reopening the filesystem. After preparation, the selected
device is checked again. Raspberry Pi Imager then owns privileged device access,
locking, writing, readback verification and eject. Its verification and system-disk
protections remain enabled. Failed preparation never reaches the native writer.

On macOS, the Imager child receives `QT_EVENT_DISPATCHER_CORE_FOUNDATION=1`.
Imager 2.0.11.1 dispatches unmount/eject operations to the main queue, which Qt's
default UNIX CLI event dispatcher does not service. The native Core Foundation
dispatcher delivers these callbacks without replacing Imager's disk handling.

| Partition | Content | Runtime access |
| --- | --- | --- |
| FAT32 boot | Stock firmware, staged Python provisioner | OS managed |
| ext4 root | Stock desktop OS and installed player setup | Read/write |
| exFAT media | `video.<extension>` and `player.json` | Read-only |

The stock `resize` boot argument is removed to protect the appended media
partition. Cloud-init is disabled. A systemd first-boot hook runs the bundled
Python provisioner, creates an unprivileged player account, configures a dedicated
labwc/LightDM session and installs the user service. Only successful setup removes
the hook and triggers the automatic reboot. Errors remain on the boot console.

The kiosk session has no panel or idle-screen manager. Autostart imports the real
Wayland environment before starting the service. The runtime validates one local
file and replaces itself with VLC; systemd retries exited processes after ten
seconds. This detects process exits, not frozen video decoding.

The custom labwc directory includes a copy of the pinned OS's
`/etc/xdg/labwc/environment`. The `-C` option replaces the configuration search
path, so omitting this file loses Pi-specific defaults, including
`WLR_DRM_FORCE_LIBLIFTOFF=1` and the Xwayland authentication wrapper. The kiosk
keeps its own autostart and window configuration; the stock desktop is not started.
`systemd-cat` connects the compositor's output to the bounded journal under
`raspi-session` instead of allowing verbose compositor output to grow a text log.

VLC explicitly uses the Pi OS `wl-dmabuf` output and `wl-xdg-shell` window
provider inside labwc. The kernel requests HDMI0 at 1920x1080/60 Hz; labwc autostart applies the same
mode with the preinstalled wlr-randr before the checkpoint, logging success or failure.
VLC scales the video to fullscreen without changing its source resolution.
The user service starts the installed PipeWire/WirePlumber services concurrently.
`pw-dump` provides output nodes and connected ALSA routes; `wpctl` unmutes the
selected HDMI node at unity volume. `PULSE_SINK` routes VLC's PulseAudio output
to that node. No extra audio packages are required. If HDMI audio is unavailable,
the player logs the reason and starts video without sound rather than blocking it.

Before every VLC launch, systemd runs the GTK startup checkpoint as ExecStartPre.
The fullscreen message "Player wird gestartet" remains for ten seconds after
the window's map event. Failure or premature closure blocks VLC; a 45-second
service startup timeout bounds missing map events. The screen uses GTK and GI
already installed in the pinned OS and does not wait for audio initialization.
Window mapping is a software checkpoint, not proof that the monitor displays it.

A separate early service disables default service dependencies and waits only
for bootfs. It records pending systemd jobs in `raspi-early-boot.txt`; it does not
order or delay graphical startup. Managed player config directories and files
are normalized to 0755/0644 during installation and repair.

LightDM's pre-start hook writes `raspi-boot.txt` directly and includes the preceding
boot's relevant journal. Hook errors do not prevent LightDM from starting.
The diagnostic exporter also has a separate, truncated-per-run stdout/stderr file,
so its own exceptions remain readable even when its report generation fails.

Diagnostics run independently of playback. journald persists logs with a 32 MiB
budget, 4 MiB journal segments and seven-day retention. A low-priority systemd
timer exports status after 30 seconds and then five minutes after each completed
export. Each probe has a five-second timeout. The boot volume retains the latest
and previous reports, each capped at 128 KiB. Reports include player/session
failures from the current and previous boot, connector state, display mode,
HDMI audio state and throttling. No diagnostic command changes display settings,
restarts services or enters the video frame loop. Small periodic I/O remains;
the limits prevent unbounded logging, not all hardware overhead or power-loss risk.

The FATtools integration is confined to exFAT. A bounded standard-file adapter
avoids its macOS raw-device ioctls. pyfatfs handles stock FAT32 independently.

No custom renderer, playback daemon, web server, playlist generation, SSH setup,
or existing-OS migration is needed. Every card is fully recreated. Unallocated
space beyond the composed image stays unused; there is no partition-resizing tool.
