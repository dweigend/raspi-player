"""Exercise whole-disk eligibility and hot-swap safety without physical devices."""

import plistlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

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


@pytest.mark.parametrize("existing_file", [True, False])
def test_mac_source_uses_filesystem_device(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, existing_file: bool
) -> None:
    """Nested paths and future images resolve through df, including spaces."""
    path = tmp_path / "video with spaces.mp4"
    if existing_file:
        path.touch()
    query = Mock(
        side_effect=[
            b"Filesystem 512-blocks Used Available Capacity Mounted on\n"
            b"/dev/disk3s5 100 20 80 20% /System/Volumes/Data\n",
            plistlib.dumps({"ParentWholeDisk": "disk3"}),
        ]
    )
    monkeypatch.setattr(devices, "command", query)
    assert devices.mac_source_disks(path) == {"/dev/disk3"}
    assert query.call_args_list[0].args[0] == [
        "df",
        "-P",
        str(path if existing_file else tmp_path),
    ]
    assert query.call_args_list[1].args[0] == [
        "diskutil",
        "info",
        "-plist",
        "/dev/disk3s5",
    ]


@pytest.mark.parametrize("apfs", [False, True])
def test_mac_rejects_source_on_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, apfs: bool
) -> None:
    """Protect files on ordinary partitions and synthetic APFS volumes alike."""
    info: dict[str, object] = {"ParentWholeDisk": "disk7"}
    if apfs:
        info = {
            "ParentWholeDisk": "disk8",
            "APFSContainerReference": "disk8",
            "APFSPhysicalStores": [{"APFSPhysicalStore": "disk7s2"}],
        }
    query = Mock(
        side_effect=[
            b"Filesystem\n/dev/disk8s1 100 20 80 20% /Volumes/My Card\n",
            plistlib.dumps(info),
        ]
    )
    monkeypatch.setattr(devices, "command", query)
    monkeypatch.setattr(devices.sys, "platform", "darwin")
    with pytest.raises(ValueError, match="contains an input file"):
        devices.require_other_disk(
            tmp_path / "video.mp4", Device("/dev/disk7", "SD", 32_000_000_000, "id")
        )


@pytest.mark.parametrize("output", [b"", b"Filesystem\nserver:/share 100 20 80\n"])
def test_mac_unknown_filesystem_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: bytes
) -> None:
    query = Mock(return_value=output)
    monkeypatch.setattr(devices, "command", query)
    with pytest.raises(ValueError, match="Cannot determine"):
        devices.mac_source_disks(tmp_path)
    query.assert_called_once()


@pytest.mark.parametrize(
    "info",
    [
        {},
        {"ParentWholeDisk": "unknown"},
        {"APFSContainerReference": "disk8"},
        {"APFSContainerReference": "disk8", "APFSPhysicalStores": []},
        {"APFSContainerReference": "disk8", "APFSPhysicalStores": [{}]},
    ],
)
def test_mac_unknown_physical_disks_fail_closed(info: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="Cannot determine"):
        devices.mac_physical_disks(info)


def test_mac_apfs_checks_every_backing_store() -> None:
    assert devices.mac_physical_disks(
        {
            "APFSContainerReference": "disk8",
            "APFSPhysicalStores": [
                {"APFSPhysicalStore": "disk0s2"},
                {"APFSPhysicalStore": "disk7s2"},
            ],
        }
    ) == {"/dev/disk0", "/dev/disk7"}
