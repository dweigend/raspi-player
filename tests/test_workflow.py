"""Prove failures and changed targets never reach the destructive writer."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from raspi_player import workflow
from raspi_player.models import Device, WriteRequest


def request(tmp_path: Path) -> WriteRequest:
    return WriteRequest(
        Device("/dev/disk7", "SD", 32_000_000_000, "id"),
        tmp_path / "video.mp4",
        tmp_path,
        tmp_path,
    )


def test_failed_preparation_never_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = Mock()
    monkeypatch.setattr(workflow, "preflight", lambda _: tmp_path / "imager")
    monkeypatch.setattr(workflow, "compose", Mock(side_effect=ValueError("bad image")))
    monkeypatch.setattr(workflow, "write_card", writer)
    with pytest.raises(ValueError, match="bad image"):
        workflow.create_card(request(tmp_path), lambda _: None)
    writer.assert_not_called()


def test_device_changed_during_preparation_never_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    writer = Mock()
    monkeypatch.setattr(workflow, "preflight", lambda _: tmp_path / "imager")
    monkeypatch.setattr(workflow, "compose", lambda inputs, output, progress: output)
    monkeypatch.setattr(
        workflow.devices, "revalidate", Mock(side_effect=ValueError("changed"))
    )
    monkeypatch.setattr(workflow, "write_card", writer)
    with pytest.raises(ValueError, match="changed"):
        workflow.create_card(request(tmp_path), lambda _: None)
    writer.assert_not_called()


def test_writer_failure_is_not_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workflow, "preflight", lambda _: tmp_path / "imager")
    monkeypatch.setattr(workflow, "compose", lambda inputs, output, progress: output)
    monkeypatch.setattr(workflow.devices, "revalidate", lambda d: d)
    monkeypatch.setattr(
        workflow, "write_card", Mock(side_effect=RuntimeError("verify failed"))
    )
    with pytest.raises(RuntimeError, match="verify failed"):
        workflow.create_card(request(tmp_path), lambda _: None)
