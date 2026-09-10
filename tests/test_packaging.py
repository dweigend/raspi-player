"""Verify portable asset discovery without launching Imager or accessing a card."""

import os
import sys
from pathlib import Path

import pytest

from raspi_player.imager import find_imager
from raspi_player.settings import offline_directory


def test_frozen_mac_assets_stay_inside_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = tmp_path / "Applications/Raspi Player.app/Contents"
    executable = contents / "MacOS/Raspi Player"
    unrelated_directory = tmp_path / "unrelated"
    unrelated_directory.mkdir()
    monkeypatch.chdir(unrelated_directory)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert offline_directory() == contents / "Resources/offline"


def test_frozen_windows_assets_stay_beside_executable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = tmp_path / "Raspi Player"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(application / "Raspi Player.exe"))

    assert offline_directory() == application / "offline"


def test_source_assets_use_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delattr(sys, "frozen", raising=False)

    assert offline_directory() == tmp_path / "offline"


@pytest.mark.skipif(os.name == "nt", reason="macOS bundle uses POSIX symlinks")
def test_mac_imager_resolves_bundled_helpers_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    contents = tmp_path / "Raspi Player.app/Contents"
    assets = contents / "Resources/offline"
    executable = contents / "Helpers/Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"
    executable.parent.mkdir(parents=True)
    executable.touch()
    assets.mkdir(parents=True)
    (assets / "imager").symlink_to("../../Helpers", target_is_directory=True)
    monkeypatch.setattr(sys, "platform", "darwin")

    assert find_imager(assets) == executable.resolve()
