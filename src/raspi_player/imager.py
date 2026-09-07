"""Delegate device locking, privileged writes, verification and eject to Imager."""

import subprocess
import sys
from pathlib import Path

from raspi_player.files import Progress
from raspi_player.models import Device


def find_imager(assets: Path) -> Path:
    """Prefer the bundled native Imager, then an existing standard installation."""
    if sys.platform == "darwin":
        suffix = "Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"
        candidates = [assets / "imager" / suffix, Path("/Applications") / suffix]
    elif sys.platform == "win32":
        import os

        installed = Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
        candidates = [
            assets / "imager/rpi-imager.exe",
            installed / "Raspberry Pi Imager/rpi-imager.exe",
        ]
    else:
        raise RuntimeError("Imager integration requires macOS or Windows.")
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError("Raspberry Pi Imager is missing. Run prepare-offline first.")


def write_card(inputs: tuple[Path, Path], device: Device, progress: Progress) -> None:
    """Write only the explicit selected disk; verification/ejection stay enabled."""
    executable, image = inputs
    args = [str(executable), "--cli", str(image), device.path]
    progress("Writing and verifying the SD card. Do not remove it…")
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ) as process:
        assert process.stdout is not None
        recent: list[str] = []
        for line in process.stdout:
            if line := line.strip():
                recent = [*recent[-9:], line]
                progress(line)
        if process.wait() != 0:
            raise RuntimeError(
                "Imager failed; the card is not ready.\n" + "\n".join(recent)
            )
    progress("Card written, verified and ejected. Insert it into your Raspberry Pi 5.")
