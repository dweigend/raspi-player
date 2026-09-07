"""Fetch pinned inputs once; normal card creation never accesses the network."""

import plistlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from raspi_player.files import Progress, copy_stream, sha256
from raspi_player.settings import BASE_SHA256, BASE_URL, IMAGER_VERSION

RELEASE = (
    f"https://github.com/raspberrypi/rpi-imager/releases/download/v{IMAGER_VERSION}"
)
IMAGER_ASSETS = {
    "darwin": (
        f"rpi-imager-v{IMAGER_VERSION}.dmg",
        "2b4c5324c5ff04aa3bfb216795ae9e01cb54400752727353e13fb21e66c528a9",
    ),
    "win32": (
        f"imager-v{IMAGER_VERSION}.exe",
        "94ffded522f3e2a38bdb9505440229e1411b80992a616ba16b2d7e73bd794130",
    ),
}
INNOUNP_ASSET = (
    "https://raw.githubusercontent.com/jrathlev/InnoUnpacker-Windows-GUI/"
    "6fb49264aacf512a093e7b4fc6fb3dd266dad31a/innounp-2/bin/innounp-267.zip",
    "ac1d98bba6588072ade06163781938df274f444bec7318069668608d1e5faae8",
)


def download(asset: tuple[str, str], destination: Path, progress: Progress) -> None:
    """Download to a temporary sibling and only activate a checksum-matched file."""
    url, expected = asset
    if destination.exists() and sha256(destination) == expected:
        progress(f"Already verified: {destination.name}")
        return
    partial = destination.with_suffix(destination.suffix + ".part")
    progress(f"Downloading {destination.name}…")
    with (
        urllib.request.urlopen(url, timeout=60) as response,
        partial.open("wb") as target,
    ):
        actual = copy_stream(response, target, progress)
    if actual != expected:
        raise ValueError(f"Checksum mismatch: {destination.name}")
    partial.replace(destination)


def extract_mac(installer: Path, destination: Path) -> None:
    """Extract the official signed application from its verified read-only DMG."""
    result = subprocess.run(
        ["hdiutil", "attach", "-readonly", "-nobrowse", "-plist", str(installer)],
        check=True,
        capture_output=True,
    )
    entries = plistlib.loads(result.stdout)["system-entities"]
    mount = next(
        Path(entry["mount-point"]) for entry in entries if "mount-point" in entry
    )
    try:
        target = destination / "Raspberry Pi Imager.app"
        if not target.exists():
            shutil.copytree(mount / target.name, target, symlinks=True)
    finally:
        subprocess.run(
            ["hdiutil", "detach", str(mount)], check=True, capture_output=True
        )


def extract_windows(installer: Path, destination: Path, progress: Progress) -> None:
    """Unpack Inno Setup without executing its installer or modifying Windows."""
    with tempfile.TemporaryDirectory(prefix="raspi-player-unpack-") as temporary:
        staging = Path(temporary)
        archive = staging / "innounp.zip"
        download(INNOUNP_ASSET, archive, progress)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extract("innounp.exe", staging)
        subprocess.run(
            [
                str(staging / "innounp.exe"),
                "-x",
                "-b",
                "-y",
                "-a",
                f"-d{staging / 'extracted'}",
                str(installer.resolve()),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        application = staging / "extracted" / "{app}"
        for name in ("rpi-imager.exe", "Qt6Core.dll", "platforms/qwindows.dll"):
            if not (application / name).is_file():
                raise ValueError(f"Unexpected Imager installer layout: missing {name}")
        shutil.copytree(application, destination, dirs_exist_ok=True)


def prepare(destination: Path, progress: Progress) -> None:
    """Prepare all native input assets for subsequent offline card creation."""
    if sys.platform not in IMAGER_ASSETS:
        raise RuntimeError("Prepare the bundle on macOS or Windows.")
    destination.mkdir(parents=True, exist_ok=True)
    download((BASE_URL, BASE_SHA256), destination / "base.img.xz", progress)
    name, digest = IMAGER_ASSETS[sys.platform]
    installer = destination / name
    download((f"{RELEASE}/{name}", digest), installer, progress)
    imager = destination / "imager"
    imager.mkdir(exist_ok=True)
    progress("Extracting Raspberry Pi Imager…")
    if sys.platform == "darwin":
        extract_mac(installer, imager)
    else:
        extract_windows(installer, imager, progress)
    progress(f"Offline assets ready: {destination.resolve()}")
