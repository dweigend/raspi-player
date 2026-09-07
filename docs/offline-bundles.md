<!-- Explain preparation of complete offline distributions. -->
# Offline bundles

Run `uv run raspi-player prepare-offline` once on each build platform. It downloads
the pinned Raspberry Pi OS Desktop archive and native Imager, checks their SHA-256
values, and puts them in `offline/`. macOS extracts the signed app from a read-only
DMG. Windows uses 7-Zip to unpack the official NSIS installer without installing it.

Run `uv run python scripts/build_app.py` to package Python, Tk and dependencies.
The resulting application lives beside its `offline` folder. End users only open
the application. Windows uses standard UAC; macOS delegates write authorization to
Imager. Build artifacts are unsigned and not notarized.

The **Offline bundles** GitHub workflow builds on both native platforms. Archive
macOS with `ditto` to retain application symlinks. Do not put image archives,
application binaries or operator videos into Git. The GitHub build artifacts
include offline inputs; they do not include operator media.

The base is Raspberry Pi OS Desktop ARM64 Trixie, 2026-06-18; Imager is 2.0.11.1.
Pins live in `settings.py` and `offline.py`. A base update requires inspection of
the real image's boot files/partition layout and a repeated hardware acceptance.
The first-boot provisioner downloads nothing: VLC, Python, labwc and LightDM must
already be present in the selected OS image.
