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

The FATtools integration is confined to exFAT. A bounded standard-file adapter
avoids its macOS raw-device ioctls. pyfatfs handles stock FAT32 independently.

No custom renderer, playback daemon, web server, playlist generation, SSH setup,
or existing-OS migration is needed. Every card is fully recreated. Unallocated
space beyond the composed image stays unused; there is no partition-resizing tool.
