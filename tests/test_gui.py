"""Verify nonblocking discovery and UI-thread updates without a display or disks."""

import queue
import threading
from unittest.mock import Mock

import pytest

from raspi_player import gui
from raspi_player.models import Device


@pytest.fixture
def window() -> gui.PlayerWindow:
    """Replace Tk widgets while retaining the actual discovery lifecycle."""
    window = gui.PlayerWindow.__new__(gui.PlayerWindow)
    window.devices = []
    window.busy = False
    window.scanning = False
    window.scan_results = queue.Queue()
    window.card = Mock()
    window.status = Mock()
    window.refresh_button = Mock()
    window.start_button = Mock()
    return window


def test_slow_discovery_does_not_block_or_touch_widgets(
    window: gui.PlayerWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    release = threading.Event()
    started = threading.Event()
    device = Device("/dev/disk7", "SD reader", 32_000_000_000, "reader")

    def discover() -> list[Device]:
        started.set()
        assert release.wait(timeout=5)
        return [device]

    monkeypatch.setattr(gui, "list_devices", discover)
    try:
        window.refresh()
        assert started.wait(timeout=5)
        assert window.scanning
        assert not window.devices
        assert window.scan_results.empty()
    finally:
        release.set()
    result = window.scan_results.get(timeout=5)
    assert not window.devices
    window.finish_scan(result)
    assert window.devices == [device]
    assert not window.scanning


def test_scan_failure_clears_stale_choices(
    window: gui.PlayerWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    window.devices = [Device("/dev/disk7", "Old card", 32_000_000_000, "old")]
    monkeypatch.setattr(gui, "list_devices", Mock(side_effect=OSError("Reader busy")))
    window.refresh()
    window.finish_scan(window.scan_results.get(timeout=5))
    assert not window.devices
    assert not window.scanning


def test_refresh_cannot_scan_during_card_creation(
    window: gui.PlayerWindow, monkeypatch: pytest.MonkeyPatch
) -> None:
    discover = Mock()
    monkeypatch.setattr(gui, "list_devices", discover)
    window.busy = True
    window.refresh()
    discover.assert_not_called()
