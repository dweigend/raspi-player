"""Fetch pinned inputs once; normal card creation never accesses the network."""

import plistlib
import shutil
import subprocess
import sys
import urllib.request
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


def extract_windows(installer: Path, destination: Path) -> None:
    """Use 7-Zip to unpack the official NSIS installer without installing it."""
    executable = shutil.which("7z") or shutil.which("7z.exe")
    if executable is None:
        candidate = Path("C:/Program Files/7-Zip/7z.exe")
        executable = str(candidate) if candidate.is_file() else None
    if executable is None:
        raise ValueError(
            "Offline-bundle preparation requires 7-Zip. "
            "End users need only the finished bundle."
        )
    subprocess.run(
        [executable, "x", "-y", f"-o{destination}", str(installer)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    if not (destination / "rpi-imager.exe").is_file():
        raise ValueError(
            "Unexpected Imager installer layout; rpi-imager.exe is missing."
        )


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
        extract_windows(installer, imager)
    progress(f"Offline assets ready: {destination.resolve()}")
