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
SYSTEM_LABWC = Path("/etc/xdg/labwc")
USERNAME = "player"


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(0o644)


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
            "Exec=/usr/bin/systemd-cat --identifier=raspi-session "
            "/usr/bin/labwc -C /etc/raspi-player/labwc\nDesktopNames=labwc\n"
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
    CONFIG.chmod(0o755)
    for name in ("play.py", "startup.py"):
        shutil.copyfile(SOURCE / name, CONFIG / name)
    install_diagnostics()
    install_labwc()
    install_media_mount()
    for path in CONFIG.rglob("*"):
        path.chmod(0o755 if path.is_dir() else 0o644)


def install_labwc() -> None:
    """Keep Pi OS graphics defaults while replacing only the kiosk UI hooks."""
    directory = CONFIG / "labwc"
    directory.mkdir(parents=True, exist_ok=True)
    # -C replaces labwc's search path, including the Pi-specific DRM environment.
    shutil.copyfile(SYSTEM_LABWC / "environment", directory / "environment")
    for name in ("autostart", "shutdown", "rc.xml"):
        shutil.copyfile(SOURCE / name, directory / name)


def install_media_mount() -> None:
    """Mount the existing video partition read-only, without changing its data."""
    Path("/srv/raspi-player").mkdir(exist_ok=True)
    fstab = Path("/etc/fstab")
    entry = (
        "/dev/mmcblk0p3 /srv/raspi-player exfat "
        "ro,nofail,nodev,nosuid,noexec,x-systemd.device-timeout=10 0 0\n"
    )
    if "/srv/raspi-player" not in fstab.read_text():
        with fstab.open("a") as stream:
            stream.write(entry)


def install_diagnostics() -> None:
    """Keep bounded journals and periodic boot-volume reports across reboots."""
    shutil.copyfile(SOURCE / "diagnose.py", CONFIG / "diagnose.py")
    shutil.copyfile(SOURCE / "boot-check.sh", CONFIG / "boot-check.sh")
    write(
        Path("/etc/systemd/system/lightdm.service.d/player-diagnostics.conf"),
        "[Service]\nExecStartPre=-/bin/sh /etc/raspi-player/boot-check.sh\n",
    )
    Path("/etc/systemd/system/graphical.target.wants/raspi-diagnostics.service").unlink(
        missing_ok=True
    )
    for suffix in ("service", "timer"):
        shutil.copyfile(
            SOURCE / f"diagnostics.{suffix}",
            Path(f"/etc/systemd/system/raspi-diagnostics.{suffix}"),
        )
    write(
        Path("/etc/systemd/journald.conf.d/player.conf"),
        "[Journal]\nStorage=persistent\nSystemMaxUse=32M\nSystemMaxFileSize=4M\n"
        "SystemKeepFree=128M\nRuntimeMaxUse=8M\nMaxRetentionSec=7day\n"
        "RateLimitIntervalSec=30s\nRateLimitBurst=300\n",
    )
    shutil.copyfile(
        SOURCE / "boot-check.service",
        Path("/etc/systemd/system/raspi-boot-check.service"),
    )
    run("systemctl", "enable", "raspi-boot-check.service", "raspi-diagnostics.timer")


def finish_setup() -> None:
    write(Path("/etc/cloud/cloud-init.disabled"), "")
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
        "systemd-cat",
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
