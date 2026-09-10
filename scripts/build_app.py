"""Build a self-contained macOS app and DMG, or a Windows portable folder.

Run after prepare-offline. Only regular build files are written; never a card.
"""

import html
import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

from markdown_it import MarkdownIt

from raspi_player.files import sha256
from raspi_player.settings import BASE_SHA256

APP_NAME = "Raspi Player"


def copy_documentation(root: Path, destination: Path) -> None:
    """Keep the illustrated instructions and upstream notices with the app."""
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("README.md", "THIRD_PARTY.md"):
        shutil.copyfile(root / name, destination / name)
    shutil.copytree(root / "docs", destination / "docs", dirs_exist_ok=True)
    # Rich already supplies MarkdownIt; no additional build dependency is needed.
    readme = (root / "README.md").read_text(encoding="utf-8")
    rendered = MarkdownIt("commonmark", {"html": True}).enable("table").render(readme)
    (destination / "README.html").write_text(
        '<!doctype html><html lang="de"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(APP_NAME)} – Anleitung</title>"
        '<link rel="stylesheet" href="docs/app.css"><body>'
        f"{rendered}</body></html>",
        encoding="utf-8",
    )


def archive_source(root: Path, destination: Path) -> None:
    """Ship current source and notices without local videos, caches or secrets."""
    included = [root / name for name in ("pyproject.toml", "uv.lock")]
    for name in ("src", "scripts", "tests", "docs"):
        included.extend(
            path
            for path in (root / name).rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )
    included.extend(root / name for name in ("README.md", "THIRD_PARTY.md"))
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(included):
            archive.write(path, Path("raspi-player") / path.relative_to(root))


def package_mac(root: Path) -> None:
    """Preserve Imager's signature and seal the completed outer app ad hoc."""
    application = root / "dist" / f"{APP_NAME}.app"
    contents = application / "Contents"
    resources = contents / "Resources"
    offline = resources / "offline"
    offline.mkdir(parents=True)
    shutil.copyfile(root / "offline/base.img.xz", offline / "base.img.xz")
    helper = "Raspberry Pi Imager.app"
    subprocess.run(
        [
            "ditto",
            str(root / "offline/imager" / helper),
            str(contents / "Helpers" / helper),
        ],
        check=True,
    )
    # Keep the existing Imager lookup while storing nested code in Helpers.
    (offline / "imager").symlink_to("../../Helpers", target_is_directory=True)
    copy_documentation(root, resources)
    subprocess.run(["codesign", "--force", "--sign", "-", str(application)], check=True)
    subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(application)], check=True
    )

    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    filename = f"Raspi-Player-{version}-macos-{platform.machine()}.dmg"
    disk_image = root / "dist" / filename
    with tempfile.TemporaryDirectory(prefix="dmg-", dir=root / "build") as temporary:
        staging = Path(temporary)
        subprocess.run(
            ["ditto", str(application), str(staging / application.name)], check=True
        )
        (staging / "Applications").symlink_to("/Applications", target_is_directory=True)
        copy_documentation(root, staging)
        archive_source(root, staging / "raspi-player-source.zip")
        (staging / "START HERE.txt").write_text(
            "Raspi Player – Installation\n\n"
            "1. Raspi Player.app auf Applications (Programme) ziehen.\n"
            "2. Raspi Player aus Programme öffnen.\n"
            "3. SD-Karte und Video auswählen; Create card startet die Vorbereitung.\n\n"
            "Achtung: Die ausgewählte SD-Karte wird vollständig gelöscht.\n"
            "Diese Ausgabe ist nicht von Apple notarisiert.\n"
            "Falls macOS sie blockiert:\n"
            "Systemeinstellungen > Datenschutz & Sicherheit > Dennoch öffnen.\n\n"
            "README.html per Doppelklick für die bebilderte Anleitung öffnen.\n"
            "Python oder Terminal sind zur Nutzung nicht erforderlich.\n",
            encoding="utf-8",
        )
        subprocess.run(
            [
                "hdiutil",
                "create",
                "-volname",
                APP_NAME,
                "-srcfolder",
                str(staging),
                "-format",
                "UDZO",
                "-ov",
                str(disk_image),
            ],
            check=True,
        )
    disk_image.with_suffix(".dmg.sha256").write_text(
        f"{sha256(disk_image)}  {filename}\n", encoding="ascii"
    )
    print(f"macOS app: {application}")
    print(f"Distributable DMG (ad-hoc signed, not notarized): {disk_image}")


def build() -> None:
    """Validate required offline inputs before starting the expensive build."""
    root = Path(__file__).resolve().parents[1]
    if sys.platform not in ("darwin", "win32"):
        raise RuntimeError("Build on macOS or Windows for that platform.")
    base = root / "offline/base.img.xz"
    helper = (
        "imager/Raspberry Pi Imager.app/Contents/MacOS/rpi-imager"
        if sys.platform == "darwin"
        else "imager/rpi-imager.exe"
    )
    if not base.is_file() or not (root / "offline" / helper).is_file():
        raise RuntimeError("Run uv run raspi-player prepare-offline before building.")
    if sha256(base) != BASE_SHA256:
        raise ValueError("Offline OS checksum mismatch. Run prepare-offline again.")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(root / "scripts/raspi-player.spec"),
        ],
        cwd=root,
        check=True,
    )
    if sys.platform == "darwin":
        package_mac(root)
        return
    target = root / "dist" / APP_NAME
    offline = target / "offline"
    offline.mkdir(exist_ok=True)
    shutil.copyfile(base, offline / "base.img.xz")
    shutil.copytree(root / "offline/imager", offline / "imager", dirs_exist_ok=True)
    copy_documentation(root, target)
    archive_source(root, target / "raspi-player-source.zip")
    print(f"Windows portable bundle: {target}")


if __name__ == "__main__":
    build()
