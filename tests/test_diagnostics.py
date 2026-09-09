"""Check bounded, failure-tolerant diagnostic exports without Linux or a real card.

Exercise report retention and failed probes; no test starts or stops playback.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock

import pytest

from raspi_player.payload import diagnose


def test_report_rotation_preserves_previous_and_caps_output(tmp_path: Path) -> None:
    diagnose.save_report(tmp_path, "first report")
    diagnose.save_report(tmp_path, "x" * (diagnose.REPORT_LIMIT + 100))
    assert (tmp_path / "raspi-diagnostics-previous.txt").read_text() == "first report"
    assert (tmp_path / "raspi-diagnostics.txt").stat().st_size == diagnose.REPORT_LIMIT
    assert not (tmp_path / "raspi-diagnostics.tmp").exists()


def test_failed_report_write_preserves_latest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnose.save_report(tmp_path, "working report")
    monkeypatch.setattr(diagnose.os, "fsync", Mock(side_effect=OSError("Disk full")))
    with pytest.raises(OSError, match="Disk full"):
        diagnose.save_report(tmp_path, "new report")
    assert (tmp_path / "raspi-diagnostics.txt").read_text() == "working report"


def test_large_log_reads_only_bounded_tail(tmp_path: Path) -> None:
    path = tmp_path / "session.log"
    path.write_bytes(b"x" * (diagnose.SECTION_LIMIT * 10) + b"LATEST ERROR")
    result = diagnose.file_tail(path)
    assert result.endswith("LATEST ERROR\n")
    assert len(result) < diagnose.SECTION_LIMIT + 200


@pytest.mark.parametrize(
    "error", [FileNotFoundError("No tool"), subprocess.TimeoutExpired("probe", 5)]
)
def test_probe_failures_are_reported_without_aborting(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    monkeypatch.setattr(diagnose.subprocess, "run", Mock(side_effect=error))
    assert str(error) in diagnose.capture(["probe"])


def test_probe_output_and_exit_status_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = Mock(
        return_value=subprocess.CompletedProcess(
            ["probe"],
            1,
            stdout=b"x" * (diagnose.SECTION_LIMIT * 2) + b"FAIL",
        )
    )
    monkeypatch.setattr(diagnose.subprocess, "run", run)
    result = diagnose.capture(["probe"])
    assert "exit=1" in result
    assert result.endswith("FAIL\n")
    assert len(result) < diagnose.SECTION_LIMIT + 100
    assert run.call_args.kwargs["timeout"] == 5


def test_disconnected_hdmi_status_is_recorded(tmp_path: Path) -> None:
    connector = tmp_path / "card1-HDMI-A-1"
    connector.mkdir()
    (connector / "status").write_text("disconnected\n")
    (connector / "modes").write_text("")
    assert "disconnected" in diagnose.display_state(tmp_path)


def test_missing_player_still_exports_system_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pwd = pytest.importorskip("pwd")
    monkeypatch.setattr(pwd, "getpwnam", Mock(side_effect=KeyError("player")))
    monkeypatch.setattr(diagnose, "BOOT", tmp_path)
    capture = Mock(return_value="probe recorded\n")
    monkeypatch.setattr(diagnose, "capture", capture)
    monkeypatch.setattr(diagnose, "display_state", Mock(return_value=""))
    monkeypatch.setattr(diagnose, "file_tail", Mock(return_value=""))
    diagnose.main()
    report = (tmp_path / "raspi-diagnostics.txt").read_text()
    assert "player account is missing" in report
    assert "probe recorded" in report
    assert not any(call.args[0][0] == "runuser" for call in capture.call_args_list)
