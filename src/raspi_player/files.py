"""Stream and verify regular files without loading videos or images into memory."""

import hashlib
from collections.abc import Callable
from pathlib import Path

from raspi_player.settings import CHUNK_SIZE, VIDEO_SUFFIXES

Progress = Callable[[str], None]


def sha256(path: Path) -> str:
    """Hash a regular local file in bounded chunks."""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_file(path: Path) -> Path:
    """Reject devices, directories, and missing or empty files."""
    path = path.resolve(strict=True)
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Expected a non-empty regular file: {path}")
    return path


def validate_video(path: Path) -> Path:
    """Validate the local input boundary; codec acceptance requires a Pi test."""
    path = require_file(path)
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        raise ValueError("Choose a video file, not a playlist or network URL.")
    return path


def copy_stream(source: object, target: object, progress: Progress) -> str:
    """Copy file-like objects, report progress, and return the written hash."""
    from typing import BinaryIO, cast

    reader, writer = cast(BinaryIO, source), cast(BinaryIO, target)
    digest = hashlib.sha256()
    copied = 0
    while block := reader.read(CHUNK_SIZE):
        writer.write(block)
        digest.update(block)
        copied += len(block)
        progress(f"Preparing image: {copied / (1024**3):.2f} GiB copied")
    return digest.hexdigest()
