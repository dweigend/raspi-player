<!-- Explain preparation of complete offline distributions. -->
# Offline bundles

Run `uv run raspi-player prepare-offline` once on each build platform. It downloads
the pinned Raspberry Pi OS Desktop archive and native Imager, checks their SHA-256
values, and puts them in `offline/`. macOS extracts the signed app from a read-only
DMG. Windows temporarily downloads checksum-pinned Innounp 2.67.11 to unpack the
official Inno Setup installer without installing it. The unpacker is only a build
tool and is not included in the finished application. No system-wide Imager
installation, registry changes, or USB driver installation occur during extraction.
The unpacker and its source/license notices are available from
[the upstream Innounp repository](https://github.com/jrathlev/InnoUnpacker-Windows-GUI/tree/6fb49264aacf512a093e7b4fc6fb3dd266dad31a/innounp-2).

Run `uv run python scripts/build_app.py` to package Python, Tk and dependencies.
The resulting application lives beside its `offline` folder. End users only open
the application. Windows uses standard UAC; macOS delegates write authorization to
Imager. Build artifacts are unsigned and not notarized.

The **Offline bundles** GitHub workflow builds on both native platforms. Archive
macOS with `ditto` to retain application symlinks. Do not put image archives,
application binaries or operator videos into Git. The GitHub build artifacts
include offline inputs; they do not include operator media.
Uploading them requires available GitHub Actions artifact storage. If the account
quota is exhausted, packaging can still succeed locally, but no downloadable
artifact is produced by that run.

The base is Raspberry Pi OS Desktop ARM64 Trixie, 2026-06-18; Imager is 2.0.11.1.
Pins live in `settings.py` and `offline.py`. A base update requires inspection of
the real image's boot files/partition layout and a repeated hardware acceptance.
The first-boot provisioner downloads nothing: VLC, Python, labwc and LightDM must
already be present in the selected OS image.
