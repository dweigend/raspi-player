# Offline bundles

Build on the target platform. Finished distributions include Python, Tk, the
pinned Raspberry Pi OS archive and native Raspberry Pi Imager. Operators need no
developer tools or runtime downloads. Their own videos are never bundled.

## Prepare and build

```sh
uv sync --locked
uv run raspi-player prepare-offline
uv run python scripts/build_app.py
```

Preparation downloads the pinned files into `offline/` and verifies their SHA-256
checksums. macOS extracts the original signed Imager application from its
read-only DMG, preserving symlinks. Windows downloads checksum-pinned Innounp
2.67.11 temporarily and unpacks the official installer without installing it.
See the [upstream unpacker source and notices](https://github.com/jrathlev/InnoUnpacker-Windows-GUI/tree/6fb49264aacf512a093e7b4fc6fb3dd266dad31a/innounp-2).
No system-wide Imager installation or USB-driver installation is performed.

The builder checks the required inputs and OS checksum before running PyInstaller.
Download installers and unpacking tools are excluded from the finished bundles.
Run the checks listed in the [main README](../README.md) before distributing.

## macOS app and DMG

The current Apple Silicon build produces:

```text
dist/Raspi Player.app
dist/Raspi-Player-0.1.0-macos-arm64.dmg
dist/Raspi-Player-0.1.0-macos-arm64.dmg.sha256
```

The version comes from `pyproject.toml`; the architecture comes from the build
host. An Intel build is named `macos-x86_64`. An arm64 build does not support Intel
Macs. The bundled Imager requires macOS 13.0 or newer in both architecture slices,
as recorded in its Mach-O `LC_BUILD_VERSION` commands.

The app is self-contained:

```text
Raspi Player.app/Contents/
  MacOS/Raspi Player
  Helpers/Raspberry Pi Imager.app/
  Resources/
    offline/
      base.img.xz
      imager -> ../../Helpers
    README.md
    README.html
    THIRD_PARTY.md
    docs/
```

The helper is copied intact after PyInstaller runs. The relative symlink keeps the
existing Imager lookup working after the app is moved. Generated card images use
the host temporary directory; the installed app does not need write access to its
own resources. macOS write authorization is delegated to Imager.

The builder seals the completed outer app with an **ad-hoc signature** and checks
the complete bundle using `codesign --verify --deep --strict`. It preserves the
upstream Imager signature. The DMG contains the app, an Applications shortcut,
`START HERE.txt`, illustrated instructions, third-party notices and a source ZIP.
`README.html` is rendered from the main README using the already installed
MarkdownIt dependency and opens offline in a browser with the bundled screenshots.
Users drag only the app to Applications. The extra PyInstaller collection directory
in `dist/` is an intermediate result, not the macOS download to distribute.

**This build is not Developer-ID signed or notarized.** The current build machine
has no valid Apple signing identity. An ad-hoc signature does not provide a
verified developer identity or remove Gatekeeper warnings. Users may need the
per-app exception described in [Apple's opening instructions](https://support.apple.com/de-de/102445).
Do not present this as a warning-free installation. A future notarized release
requires an Apple Developer ID, a suitable signing pipeline and Apple's notary
service; these are not configured by the current builder.

Distribute the DMG together with its checksum. From its containing directory,
maintainers can verify it with:

```sh
shasum -a 256 -c Raspi-Player-0.1.0-macos-arm64.dmg.sha256
```

## Windows portable bundle

On Windows, `dist/Raspi Player/` contains the executable, runtime, `offline/`,
documentation and source archive. Keep this complete folder together. Windows
uses standard UAC for writing. A macOS build cannot generate a Windows executable.

## Distribution and acceptance

The macOS DMG and checksum are distributed through
[GitHub Releases](https://github.com/dweigend/raspi-player/releases/tag/v0.1.0).
The repository is private: recipients must sign in with an account that has
repository access. A private release URL is not an anonymous public download.
The main README links directly to the DMG and explains first-launch approval,
the Mac login-password prompt and the separate administrator prompt for writing.

An App Store submission is not required for this distribution route. See the
[reviewed Apple terms and opening instructions](apple-distribution.md).

The **Offline bundles** workflow runs manually or when a `v*` tag is pushed.
Both triggers produce native build artifacts. A tag run also creates a **draft**
GitHub release containing the macOS DMG, its checksum and the Windows ZIP after
both platform builds succeed. A maintainer must review and publish that draft;
the workflow does not publish it automatically or modify an already published
release. Manual runs only upload artifacts. A maintainer may also publish a
locally verified build directly through GitHub Releases.
Workflow artifacts require repository access, expire after 14 days and depend on
available Actions storage. A successful local build does not prove that a
downloadable artifact or release has been uploaded.

Before release, open the app after copying it from the DMG, check card discovery
without writing, and confirm its offline assets and helper resolve within the app.
Record the build host and architecture. Run the separate
[hardware acceptance checks](validation.md) for writing, safe eject and actual Pi
playback. The README screenshots show the built app's initial window and a
simulated card selection; they are not hardware-test evidence.

Do not commit image archives, application binaries or operator videos. Retain
[third-party notices](../THIRD_PARTY.md), upstream licenses and application source
when sharing distributions.

The base is Raspberry Pi OS Desktop ARM64 Trixie, 2026-06-18; Imager is 2.0.11.1.
Pins live in `settings.py` and `offline.py`. Changing the base requires inspection
of its real boot files and partition layout plus repeated hardware acceptance.
The first-boot provisioner downloads nothing: VLC, Python, labwc, LightDM and
wlr-randr must already be present in the selected OS image.
