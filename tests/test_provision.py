"""Check kiosk setup preserves OS graphics defaults without starting Linux services.

Use temporary directories; account management and physical cards are out of scope.
"""

from pathlib import Path

import pytest

pytest.importorskip("pwd")
from raspi_player.payload import provision  # noqa: E402


def test_kiosk_retains_distro_environment_but_uses_own_autostart(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    distro, source, config = (
        tmp_path / name for name in ("distro", "source", "config")
    )
    distro.mkdir()
    source.mkdir()
    environment = "WLR_DRM_FORCE_LIBLIFTOFF=1\nWLR_XWAYLAND=/usr/bin/xwayland-xauth\n"
    (distro / "environment").write_text(environment)
    (distro / "autostart").write_text("start-desktop-panel")
    for name in ("autostart", "shutdown", "rc.xml"):
        (source / name).write_text(f"kiosk {name}")
    monkeypatch.setattr(provision, "SYSTEM_LABWC", distro)
    monkeypatch.setattr(provision, "SOURCE", source)
    monkeypatch.setattr(provision, "CONFIG", config)
    provision.install_labwc()
    assert (config / "labwc/environment").read_text() == environment
    assert (config / "labwc/autostart").read_text() == "kiosk autostart"


def test_missing_distro_environment_fails_before_installing_kiosk_hooks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(provision, "SYSTEM_LABWC", tmp_path / "missing")
    monkeypatch.setattr(provision, "SOURCE", tmp_path / "source")
    monkeypatch.setattr(provision, "CONFIG", tmp_path / "config")
    with pytest.raises(FileNotFoundError):
        provision.install_labwc()
    assert not (tmp_path / "config/labwc/autostart").exists()
