"""Exercise whole-disk eligibility and hot-swap safety without physical devices."""

from dataclasses import replace

import pytest

from raspi_player import devices
from raspi_player.devices import mac_device, windows_device
from raspi_player.models import Device


@pytest.fixture
def mac_info() -> dict[str, object]:
    return {
        "DeviceIdentifier": "disk7",
        "Internal": False,
        "WholeDisk": True,
        "VirtualOrPhysical": "Physical",
        "Writable": True,
        "TotalSize": 32_000_000_000,
        "DeviceBlockSize": 512,
        "MediaName": "USB SD Reader",
        "DeviceTreePath": "usb/card-reader/1",
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("Internal", True),
        ("WholeDisk", False),
        ("Writable", False),
        ("VirtualOrPhysical", "Virtual"),
        ("DeviceIdentifier", "disk7s1"),
        ("TotalSize", 0),
        ("TotalSize", "32000000000"),
        ("DeviceBlockSize", 4096),
    ],
)
def test_mac_rejects_unsafe_disks(
    mac_info: dict[str, object], field: str, value: object
) -> None:
    mac_info[field] = value
    assert mac_device(mac_info) is None


def test_mac_accepts_external_and_internal_sd_reader(
    mac_info: dict[str, object],
) -> None:
    assert mac_device(mac_info) is not None
    mac_info.update(Internal=True, RemovableMedia=True, BusProtocol="Secure Digital")
    assert mac_device(mac_info) is not None


def test_mac_requires_native_whole_disk_field(mac_info: dict[str, object]) -> None:
    """An unrelated Whole field must not replace diskutil's WholeDisk flag."""
    del mac_info["WholeDisk"]
    mac_info["Whole"] = True
    assert mac_device(mac_info) is None


def test_mac_list_includes_builtin_sd_reader(
    mac_info: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Replay diskutil's native plist shape through discovery, not just parsing."""
    import plistlib

    mac_info.update(Internal=True, RemovableMedia=True, BusProtocol="Secure Digital")
    responses = iter(
        [plistlib.dumps({"WholeDisks": ["disk7"]}), plistlib.dumps(mac_info)]
    )
    monkeypatch.setattr(devices.sys, "platform", "darwin")
    monkeypatch.setattr(devices, "command", lambda args: next(responses))
    assert [device.path for device in devices.list_devices()] == ["/dev/disk7"]


def test_windows_blocks_system_disk_even_when_usb() -> None:
    info = {
        "Number": 2,
        "Size": 32_000_000_000,
        "BusType": "USB",
        "IsBoot": False,
        "IsSystem": False,
        "IsReadOnly": False,
        "LogicalSectorSize": 512,
        "UniqueId": "reader-123",
    }
    assert windows_device(info) is not None
    info["IsSystem"] = True
    assert windows_device(info) is None
    del info["IsSystem"]
    assert windows_device(info) is None


def test_revalidation_detects_same_number_different_card(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected = Device("/dev/disk7", "Reader", 32_000_000_000, "card-1")
    monkeypatch.setattr(
        devices, "list_devices", lambda: [replace(selected, identity="card-2")]
    )
    with pytest.raises(ValueError, match="changed or disappeared"):
        devices.revalidate(selected)
