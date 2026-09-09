"""Configure a freshly imaged Pi offline, then retire the first-boot hook.

Runs once as root on the pinned Raspberry Pi OS Desktop image. It never installs
packages or modifies the video partition; unsuccessful setup remains retryable.
"""

import configparser
import os
import pwd
import shutil
import subprocess
from pathlib import Path

SOURCE = Path("/boot/firmware/player")
CONFIG = Path("/etc/raspi-player")
USERNAME = "player"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def create_user() -> pwd.struct_passwd:
    # The official helper completes OS-specific first-user/wizard cleanup.
    run("/usr/lib/userconf-pi/userconf", USERNAME, "")
    run("usermod", "--groups", "video,audio,render,input", USERNAME)
    Path("/etc/sudoers.d/010_pi-nopasswd").unlink(missing_ok=True)
    return pwd.getpwnam(USERNAME)


def install_session(user: pwd.struct_passwd) -> None:
    directory = Path(user.pw_dir) / ".config/systemd/user"
    directory.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / "player.service", directory / "raspi-player.service")
    for path in [Path(user.pw_dir) / ".config", *Path(user.pw_dir).rglob("*")]:
        os.chown(path, user.pw_uid, user.pw_gid)
    write(
        Path("/usr/share/wayland-sessions/raspi-player.desktop"),
        (
            "[Desktop Entry]\nName=Raspi Player\nType=Application\n"
            "Exec=labwc -C /etc/raspi-player/labwc\nDesktopNames=labwc\n"
        ),
    )
    configure_lightdm(Path("/etc/lightdm/lightdm.conf"))


def configure_lightdm(path: Path) -> None:
    """Update the authoritative main config, which overrides LightDM drop-ins."""
    parser = configparser.ConfigParser(interpolation=None, strict=False)
    parser.read(path)
    if not parser.has_section("Seat:*"):
        parser.add_section("Seat:*")
    for key, value in {
        "autologin-user": USERNAME,
        "autologin-user-timeout": "0",
        "user-session": "raspi-player",
        "autologin-session": "raspi-player",
    }.items():
        parser.set("Seat:*", key, value)
    with path.open("w") as stream:
        parser.write(stream, space_around_delimiters=False)


def install_player() -> None:
    CONFIG.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE / "play.py", CONFIG / "play.py")
    for name in ("autostart", "shutdown", "rc.xml"):
        target = CONFIG / "labwc" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / name, target)
    Path("/srv/raspi-player").mkdir(exist_ok=True)
    fstab = Path("/etc/fstab")
    entry = (
        "/dev/mmcblk0p3 /srv/raspi-player exfat "
        "ro,nofail,nodev,nosuid,noexec,x-systemd.device-timeout=10 0 0\n"
    )
    if "/srv/raspi-player" not in fstab.read_text():
        with fstab.open("a") as stream:
            stream.write(entry)


def finish_setup() -> None:
    write(Path("/etc/cloud/cloud-init.disabled"), "")
    write(
        Path("/etc/systemd/journald.conf.d/player.conf"),
        "[Journal]\nStorage=volatile\nRuntimeMaxUse=32M\n",
    )
    run("systemctl", "set-default", "graphical.target")
    run("systemctl", "enable", "lightdm.service")
    cmdline = Path("/boot/firmware/cmdline.txt")
    args = [
        a
        for a in cmdline.read_text().split()
        if not a.startswith(("systemd.run", "systemd.unit="))
    ]
    temporary = cmdline.with_suffix(".tmp")
    temporary.write_text(" ".join(args) + "\n")
    temporary.replace(cmdline)
    os.sync()


def main() -> None:
    for binary in (
        "vlc",
        "pw-dump",
        "wpctl",
        "labwc",
        "lightdm",
        "/usr/lib/userconf-pi/userconf",
    ):
        if shutil.which(binary) is None:
            raise RuntimeError(f"Required preinstalled program is missing: {binary}")
    user = create_user()
    install_player()
    install_session(user)
    finish_setup()


if __name__ == "__main__":
    main()
