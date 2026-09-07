<!-- Record official and upstream sources supporting implementation choices. -->
# References

- [Raspberry Pi OS and VLC](https://www.raspberrypi.com/documentation/computers/os.html)
- [Pinned OS image, hashes and SBOM](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-06-19/)
- [Imager CLI implementation](https://github.com/raspberrypi/rpi-imager/blob/v2.0.11.1/src/cli.cpp)
- [Imager release assets](https://github.com/raspberrypi/rpi-imager/releases/tag/v2.0.11.1)
- [labwc session integration](https://labwc.github.io/integration.html)
- [VLC options](https://github.com/videolan/vlc/blob/3.0.x/src/libvlc-module.c)
- [pyfatfs source](https://github.com/nathanhi/pyfatfs)
- [FATtools exFAT implementation](https://github.com/maxpat78/FATtools)
- [Python Tkinter](https://docs.python.org/3/library/tkinter.html)
- [uv project workflows](https://docs.astral.sh/uv/guides/projects/)

The initial German drafts considered manual installation and SSH provisioning.
The implemented workflow instead prepares the complete replacement card on the
computer, independently of its previous contents.
