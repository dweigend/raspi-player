<!-- Identify upstream components bundled with the card creator. -->
# Third-party components

Retain upstream license files when distributing portable bundles. The unchanged
OS download is verified before local customization. `uv.lock` records all Python
versions. This repository does not claim authorship of upstream components.

| Component | Purpose | Source / license |
| --- | --- | --- |
| Raspberry Pi OS Desktop ARM64, 2026-06-18 | Pi runtime, VLC, labwc and Python | [Image archive and SBOM](https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2026-06-19/) |
| Raspberry Pi Imager 2.0.11.1 | Device writing, verification and eject | [Apache-2.0 and bundled notices](https://github.com/raspberrypi/rpi-imager/tree/v2.0.11.1) |
| FATtools 1.1.23 | exFAT image filesystem | [GPL source](https://github.com/maxpat78/FATtools) |
| pyfatfs 1.1.0 | Boot FAT32 editing | [MIT source](https://github.com/nathanhi/pyfatfs) |
| Python / Tk | Runtime and native GUI | [Python licensing](https://docs.python.org/3/license.html) |
| Rich | Developer CLI output | [MIT source](https://github.com/Textualize/rich) |
| PyInstaller | Application packaging | [License and bootloader exception](https://pyinstaller.org/en/stable/license.html) |

PyFilesystem still uses `pkg_resources`, so setuptools is constrained below 81.
This compatibility dependency is host-only. Provide application source and these
upstream notices with distributions. Do not strip licenses from native binaries.
