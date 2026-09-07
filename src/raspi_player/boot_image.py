"""Customize only the boot FAT of the pinned OS; root setup runs offline on Pi."""

from pathlib import Path

from pyfatfs.FSInfo import FSInfo
from pyfatfs.PyFatFS import PyFatFS

from raspi_player.partitions import read_partitions
from raspi_player.settings import PAYLOAD

FIRST_BOOT_ARGS = (
    "systemd.run=/boot/firmware/player-firstboot.sh",
    "systemd.run_success_action=reboot",
    "systemd.unit=kernel-command-line.target",
)


def player_cmdline(original: str) -> str:
    """Disable stock resizing/cloud setup before adding unattended provisioning."""
    removed = ("init=", "systemd.run", "systemd.unit=", "cloud-init=", "consoleblank=")
    args = [a for a in original.split() if a != "resize" and not a.startswith(removed)]
    args.extend(["cloud-init=disabled", "consoleblank=0", *FIRST_BOOT_ARGS])
    return " ".join(args) + "\n"


def configure_boot(image: Path) -> None:
    """Stage bundled Python setup and player assets, preserving firmware files."""
    boot = read_partitions(image)[0]
    with PyFatFS(str(image), offset=boot.offset) as fs:
        original = fs.readtext("cmdline.txt")
        replace_file(fs, "cmdline.txt", player_cmdline(original).encode())
        fs.makedirs("player", recreate=True)
        for source in sorted(PAYLOAD.iterdir()):
            if source.is_file():
                replace_file(fs, f"player/{source.name}", source.read_bytes())
        replace_file(fs, "player-firstboot.sh", (PAYLOAD / "firstboot.sh").read_bytes())
    verify_boot(image)
    refresh_space_info(image)


def refresh_space_info(image: Path) -> None:
    """Refresh FAT32 free-space hints that pyfatfs does not update after writes."""
    boot = read_partitions(image)[0]
    with PyFatFS(str(image), offset=boot.offset, read_only=True) as fs:
        header = fs.fs.bpb_header
        clusters = (header["BPB_TotSec32"] - fs.fs.first_data_sector) // header[
            "BPB_SecPerClus"
        ]
        free = sum(value == 0 for value in fs.fs.fat[2 : clusters + 2])
        info = bytes(FSInfo(free_count=free, next_free=0xFFFFFFFF))
        sectors = [header["BPB_FSInfo"], header["BPB_BkBootSec"] + header["BPB_FSInfo"]]
    with image.open("r+b") as stream:
        for sector in sectors:
            if not 0 < sector * 512 < boot.size:
                raise ValueError("Invalid FAT32 free-space sector location.")
            stream.seek(boot.offset + sector * 512)
            stream.write(info)


def replace_file(fs: PyFatFS, name: str, data: bytes) -> None:
    """Avoid stale FAT chains when a replacement changes an existing file's size."""
    if fs.exists(name):
        fs.remove(name)
    fs.writebytes(name, data)


def verify_boot(image: Path) -> None:
    """Reopen boot metadata and verify every staged file before allowing a write."""
    boot = read_partitions(image)[0]
    with PyFatFS(str(image), offset=boot.offset, read_only=True) as fs:
        args = fs.readtext("cmdline.txt").split()
        if not all(arg in args for arg in FIRST_BOOT_ARGS) or "resize" in args:
            raise ValueError("First-boot configuration did not survive image readback.")
        for source in PAYLOAD.iterdir():
            if (
                source.is_file()
                and fs.readbytes(f"player/{source.name}") != source.read_bytes()
            ):
                raise ValueError(
                    f"First-boot payload failed verification: {source.name}"
                )
