<!-- Record official and upstream sources supporting implementation choices. -->
# References

- [Raspberry Pi OS and VLC](https://www.raspberrypi.com/documentation/computers/os.html)
- [Pinned OS image, hashes and SBOM](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-06-19/)
- [Imager CLI implementation](https://github.com/raspberrypi/rpi-imager/blob/v2.0.11.1/src/cli.cpp)
- [Imager release assets](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.11.1)
- [labwc session integration](https://labwc.github.io/integration.html)
- [labwc configuration search and environment](https://labwc.github.io/labwc-config.5.html)
- [systemd journal storage and rotation](https://github.com/systemd/systemd/blob/v257/man/journald.conf.xml)
- [systemd periodic timers](https://github.com/systemd/systemd/blob/v257/man/systemd.timer.xml)
- [systemd-cat session output](https://github.com/systemd/systemd/blob/v257/man/systemd-cat.xml)
- [VLC options](https://github.com/videolan/vlc/blob/3.0.x/src/libvlc-module.c)
- [Pi OS VLC Wayland window support](https://github.com/RPi-Distro/vlc/blob/pios/trixie/debian/patches/0039-wl_xdg_shell-Create-an-updated-version-of-xdg-shell.patch)
- [Pi OS VLC Wayland video output](https://github.com/RPi-Distro/vlc/blob/pios/trixie/debian/patches/0036-video_output-wayland-Add-dmabuf-output.patch)
- [PipeWire JSON state](https://docs.pipewire.org/page_man_pw-dump_1.html)
- [PipeWire ALSA route information](https://github.com/PipeWire/pipewire/blob/1.4.2/spa/plugins/alsa/alsa-acp-device.c)
- [WirePlumber control commands](https://github.com/PipeWire/wireplumber/blob/0.5.8/src/tools/wpctl.c)
- [pyfatfs source](https://github.com/nathanhi/pyfatfs)
- [FATtools exFAT implementation](https://github.com/maxpat78/FATtools)
- [Python Tkinter](https://docs.python.org/3/library/tkinter.html)
- [uv project workflows](https://docs.astral.sh/uv/guides/projects/)

The initial German drafts considered manual installation and SSH provisioning.
The implemented workflow instead prepares the complete replacement card on the
computer, independently of its previous contents.
