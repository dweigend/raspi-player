"""Expose the GUI and non-destructive preparation commands using argparse."""

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console

from raspi_player.settings import offline_directory


def elevate_windows() -> bool:
    """Use standard UAC for the native writer when launching from Python source."""
    if sys.platform != "win32":
        return False
    import ctypes

    if ctypes.windll.shell32.IsUserAnAdmin():
        return False
    args = (
        sys.argv[1:]
        if getattr(sys, "frozen", False)
        else ["-m", "raspi_player", *sys.argv[1:]]
    )
    code = ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, subprocess.list2cmdline(args), str(Path.cwd()), 1
    )
    if code <= 32:
        raise RuntimeError("Administrator access was declined; no card was changed.")
    return True


def parser() -> argparse.ArgumentParser:
    """Keep destructive writing in the GUI's explicit card confirmation flow."""
    result = argparse.ArgumentParser(
        description="Create offline Raspberry Pi 5 video cards."
    )
    result.add_argument(
        "--assets", type=Path, default=None, help="Offline asset directory"
    )
    commands = result.add_subparsers(dest="command")
    commands.add_parser(
        "prepare-offline", help="Download and verify the offline assets once"
    )
    commands.add_parser("disks", help="List eligible cards without changing them")
    image = commands.add_parser(
        "image", help="Prepare a local image only; never write a card"
    )
    image.add_argument("video", type=Path)
    image.add_argument("output", type=Path)
    return result


def main() -> None:
    """Launch the GUI by default; handle expected failures without success claims."""
    args = parser().parse_args()
    assets = args.assets or offline_directory()
    console = Console()
    try:
        dispatch(args, assets, console)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        console.print(f"Error: {error}", style="red", markup=False)
        raise SystemExit(1) from error


def dispatch(args: argparse.Namespace, assets: Path, console: Console) -> None:
    if args.command == "prepare-offline":
        from raspi_player.offline import prepare

        prepare(assets, lambda text: console.print(text, markup=False))
    elif args.command == "image":
        from raspi_player.composer import compose

        compose(
            (assets / "base.img.xz", args.video),
            args.output,
            lambda text: console.print(text, markup=False),
        )
    elif args.command == "disks":
        from raspi_player.devices import list_devices

        for device in list_devices():
            console.print(device.label, markup=False)
    elif not elevate_windows():
        from raspi_player.gui import launch

        launch(assets)
