# Package the native GUI with explicit macOS identity and privacy descriptions.
# Bundles host code and runtime dependencies; build_app.py adds offline inputs.
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH).parent
datas, binaries, hiddenimports = [], [], []
for package in ("raspi_player", "FATtools", "pyfatfs", "fs"):
    package_data, package_binaries, package_imports = collect_all(package)
    datas.extend(package_data)
    binaries.extend(package_binaries)
    hiddenimports.extend(package_imports)

analysis = Analysis(
    [str(root / "src/raspi_player/__main__.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="Raspi Player",
    console=False,
    uac_admin=sys.platform == "win32",
)
collection = COLLECT(
    executable, analysis.binaries, analysis.datas, name="Raspi Player"
)
if sys.platform == "darwin":
    application = BUNDLE(
        collection,
        name="Raspi Player.app",
        bundle_identifier="com.dweigend.raspi-player",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "CFBundleVersion": "0.1.0",
            "LSMinimumSystemVersion": "13.0",
            "NSHighResolutionCapable": True,
            "NSRemovableVolumesUsageDescription": (
                "Raspi Player needs access to detect your SD card and prepare "
                "it as a video player, only after you confirm erasing it."
            ),
            "NSDocumentsFolderUsageDescription": (
                "Raspi Player reads your selected video and offline assets "
                "from Documents to prepare the SD card."
            ),
            "NSDownloadsFolderUsageDescription": (
                "Raspi Player reads your selected video and offline assets "
                "from Downloads to prepare the SD card."
            ),
        },
    )
