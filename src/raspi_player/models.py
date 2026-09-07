"""Represent explicit write targets and immutable card-creation inputs."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Device:
    """A whole removable device identified before any destructive operation."""

    path: str
    name: str
    size: int
    identity: str

    @property
    def label(self) -> str:
        return f"{self.name} — {self.size / 1_000_000_000:.1f} GB — {self.path}"


@dataclass(frozen=True)
class WriteRequest:
    """Bind an explicit device selection to local source files and workspace."""

    device: Device
    video: Path
    assets: Path
    workspace: Path
