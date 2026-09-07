"""Package the native Python GUI and offline inputs; never access a card.

Run through uv after prepare-offline. Produces an unsigned portable folder.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def build() -> None:
    root = Path(__file__).resolve().parents[1]
    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "Raspi Player",
    ]
    for package in ("raspi_player", "FATtools", "pyfatfs", "fs"):
        args.extend(["--collect-all", package])
    if sys.platform == "win32":
        args.append("--uac-admin")
    args.append(str(root / "src/raspi_player/__main__.py"))
    subprocess.run(args, cwd=root, check=True)
    target = root / "dist"
    if sys.platform == "win32":
        target /= "Raspi Player"
    if not (root / "offline/base.img.xz").is_file():
        raise RuntimeError("Run prepare-offline before building the offline bundle.")
    shutil.copytree(
        root / "offline", target / "offline", dirs_exist_ok=True, symlinks=True
    )
    for name in ("README.md", "THIRD_PARTY.md"):
        shutil.copyfile(root / name, target / name)
    print(f"Portable bundle: {target}")


if __name__ == "__main__":
    build()
