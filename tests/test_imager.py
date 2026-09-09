"""Verify native writer launch settings without opening or writing any disk.

Keep macOS callback delivery and the writer's verification protections intact.
"""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from raspi_player import imager
from raspi_player.models import Device


@pytest.mark.parametrize("platform", ["darwin", "win32"])
def test_writer_launch_environment(
    platform: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only the macOS child gets the native event dispatcher; retain its environment."""
    monkeypatch.setattr(imager.sys, "platform", platform)
    monkeypatch.setenv("QT_EVENT_DISPATCHER_CORE_FOUNDATION", "0")
    monkeypatch.setenv("IMAGER_TEST_INHERITED", "preserved")
    process = Mock(stdout=iter(["Writing: 50%\n", "Write successful.\n"]))
    process.wait.return_value = 0
    launcher = Mock()
    launcher.return_value.__enter__ = Mock(return_value=process)
    launcher.return_value.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(imager.subprocess, "Popen", launcher)
    imager.write_card(
        (Path("imager"), Path("card.img")),
        Device("/dev/disk7", "SD", 32_000_000_000, "id"),
        Mock(),
    )
    assert launcher.call_args.args[0] == ["imager", "--cli", "card.img", "/dev/disk7"]
    environment = launcher.call_args.kwargs["env"]
    assert environment["QT_EVENT_DISPATCHER_CORE_FOUNDATION"] == (
        "1" if platform == "darwin" else "0"
    )
    assert environment["IMAGER_TEST_INHERITED"] == "preserved"
    assert os.environ["QT_EVENT_DISPATCHER_CORE_FOUNDATION"] == "0"
