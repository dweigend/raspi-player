"""Discover removable whole disks via native structured APIs; fail closed."""

import json
import plistlib
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from raspi_player.models import Device

WINDOWS_DISKS = (
    "Get-Disk | Select-Object Number,FriendlyName,Size,UniqueId,SerialNumber,"
    "BusType,IsBoot,IsSystem,IsReadOnly,LogicalSectorSize | ConvertTo-Json -Compress"
)


def command(args: list[str]) -> bytes:
    """Execute a native read-only query without shell interpolation."""
    return subprocess.run(args, check=True, capture_output=True, timeout=30).stdout


def powershell(script: str) -> bytes:
    return command(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    )


def mac_device(info: Mapping[str, object]) -> Device | None:
    """Accept external physical media and removable built-in SD-reader media."""
    identifier = info.get("DeviceIdentifier")
    removable = info.get("RemovableMedia") is True
    external = info.get("Internal") is False
    sd_reader = info.get("BusProtocol") in ("Secure Digital", "SD") and removable
    if not (external or sd_reader) or info.get("Whole") is not True:
        return None
    if info.get("VirtualOrPhysical") != "Physical" or info.get("Writable") is not True:
        return None
    if not isinstance(identifier, str) or not re.fullmatch(r"disk\d+", identifier):
        return None
    size, sector = info.get("TotalSize"), info.get("DeviceBlockSize")
    if type(size) is not int or size <= 0 or sector != 512:
        return None
    name = str(info.get("MediaName", identifier))
    identity = str(info.get("DeviceTreePath", ""))
    return Device(f"/dev/{identifier}", name, size, identity)


def windows_device(info: Mapping[str, object]) -> Device | None:
    """Reject boot/system disks and unknown buses or protection states."""
    if info.get("BusType") not in ("USB", "SD", "MMC", 7, 12, 13):
        return None
    if any(info.get(key) is not False for key in ("IsBoot", "IsSystem", "IsReadOnly")):
        return None
    number, size = info.get("Number"), info.get("Size")
    if type(number) is not int or number < 0 or type(size) is not int or size <= 0:
        return None
    if info.get("LogicalSectorSize") != 512:
        return None
    identity = str(info.get("UniqueId") or info.get("SerialNumber") or "")
    return Device(
        rf"\\.\PhysicalDrive{number}",
        str(info.get("FriendlyName", "SD card")),
        size,
        identity,
    )


def list_devices() -> list[Device]:
    """List eligible devices; never select a default disk."""
    if sys.platform == "darwin":
        listing = plistlib.loads(command(["diskutil", "list", "-plist", "physical"]))
        devices = []
        for identifier in listing.get("WholeDisks", []):
            info = plistlib.loads(command(["diskutil", "info", "-plist", identifier]))
            if device := mac_device(info):
                devices.append(device)
        return devices
    if sys.platform == "win32":
        rows = json.loads(powershell(WINDOWS_DISKS).decode("utf-8-sig") or "[]")
        rows = rows if isinstance(rows, list) else [rows]
        return [
            device
            for row in rows
            if isinstance(row, dict) and (device := windows_device(row))
        ]
    raise RuntimeError("Card writing is supported on macOS and Windows only.")


def revalidate(selected: Device) -> Device:
    """Detect unplug/replug, changed capacity, and loss of eligibility."""
    matches = [device for device in list_devices() if device == selected]
    if len(matches) != 1:
        raise ValueError(
            "The selected card changed or disappeared. Refresh and select it again."
        )
    return matches[0]


def require_other_disk(path: Path, selected: Device) -> None:
    """Do not erase a card that holds the video, image, or application assets."""
    path = path.resolve()
    if sys.platform == "darwin":
        info = plistlib.loads(command(["diskutil", "info", "-plist", str(path.parent)]))
        whole = info.get("ParentWholeDisk") or info.get("DeviceIdentifier")
        if whole is None:
            raise ValueError(f"Cannot determine the source disk: {path}")
        source = f"/dev/{whole}"
    elif sys.platform == "win32":
        drive = path.drive
        if not re.fullmatch(r"[A-Za-z]:", drive):
            raise ValueError("Use local drive-letter paths for source files.")
        script = f"(Get-Partition -DriveLetter '{drive[0]}' | Get-Disk).Number"
        number = powershell(script).decode().strip()
        if not number.isdecimal():
            raise ValueError(f"Cannot determine the source disk: {path}")
        source = rf"\\.\PhysicalDrive{number}"
    else:
        raise RuntimeError("Unsupported card-writing platform.")
    if source == selected.path:
        raise ValueError(
            "The selected card contains an input file. Move it to the computer first."
        )
