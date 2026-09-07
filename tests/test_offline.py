"""Check Windows bundle extraction boundaries without running native binaries."""

import shutil
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from raspi_player import offline


@pytest.mark.parametrize("complete", [True, False])
def test_windows_extracts_application_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, complete: bool
) -> None:
    archive = tmp_path / "unpacker.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("innounp.exe", b"test unpacker")
    monkeypatch.setattr(
        offline,
        "download",
        lambda asset, path, progress: shutil.copyfile(archive, path),
    )

    def extract(args: list[str], **kwargs: object) -> None:
        destination = Path(next(arg[2:] for arg in args if arg.startswith("-d")))
        application = destination / "{app}"
        application.mkdir(parents=True)
        (application / "rpi-imager.exe").write_bytes(b"application")
        if complete:
            (application / "Qt6Core.dll").touch()
            (application / "platforms").mkdir()
            (application / "platforms/qwindows.dll").touch()

    runner = Mock(side_effect=extract)
    monkeypatch.setattr(offline.subprocess, "run", runner)
    destination = tmp_path / "imager"
    if not complete:
        with pytest.raises(ValueError, match="Qt6Core.dll"):
            offline.extract_windows(tmp_path / "setup.exe", destination, lambda _: None)
        assert not destination.exists()
        return
    offline.extract_windows(tmp_path / "setup.exe", destination, lambda _: None)
    assert (destination / "platforms/qwindows.dll").is_file()
    assert not (destination / "innounp.exe").exists()
    assert Path(runner.call_args.args[0][0]).name == "innounp.exe"
