"""Export bounded player diagnostics to the Mac-readable boot partition.

Runs as a low-priority systemd timer job, independently of playback and LightDM.
Reads status only; keeps two small reports and never restarts or reconfigures AV.
"""

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REPORT_LIMIT = 128 * 1024
SECTION_LIMIT = 12 * 1024
BOOT = Path("/boot/firmware")


def capture(command: list[str]) -> str:
    """Keep a failed or stalled diagnostic command from blocking later sections."""
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=5,
            check=False,
        )
        output = result.stdout[-SECTION_LIMIT:].decode("utf-8", errors="replace")
        return f"$ {' '.join(command)}\nexit={result.returncode}\n{output}\n"
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"$ {' '.join(command)}\n{error}\n"


def file_tail(path: Path) -> str:
    """Read only the end of a log, even when a crashing session grows it rapidly."""
    try:
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - SECTION_LIMIT))
            output = stream.read(SECTION_LIMIT).decode("utf-8", errors="replace")
        return f"\n--- {path} ---\n{output}\n"
    except OSError as error:
        return f"\n--- {path} ---\n{error}\n"


def display_state(root: Path) -> str:
    """Read connector state without changing modes or acquiring the display."""
    paths = sorted(root.glob("card*-HDMI-A-*/status"))
    paths += sorted(root.glob("card*-HDMI-A-*/modes"))
    return "".join(file_tail(path) for path in paths)


def user_commands(uid: int) -> list[list[str]]:
    """Inspect the existing player's user manager and audio graph."""
    prefix = [
        "runuser",
        "-u",
        "player",
        "--",
        "env",
        f"XDG_RUNTIME_DIR=/run/user/{uid}",
    ]
    return [
        prefix
        + [
            "systemctl",
            "--user",
            "show",
            "raspi-player.service",
            "-p",
            "ActiveState,SubState,NRestarts,ExecMainStatus,Result",
        ],
        prefix + ["wpctl", "status", "-n"],
    ]


def commands(uid: int | None) -> list[list[str]]:
    """Limit journal output to the player/session plus recent kernel diagnostics."""
    journal = ["journalctl", "--no-pager", "-o", "short-iso", "-n", "100"]
    session = [
        "_SYSTEMD_UNIT=lightdm.service",
        "+",
        "_SYSTEMD_USER_UNIT=raspi-player.service",
        "+",
        "SYSLOG_IDENTIFIER=raspi-session",
    ]
    return [
        [
            "systemctl",
            "show",
            "lightdm",
            "-p",
            "ActiveState,SubState,NRestarts,ExecMainStatus,Result",
        ],
        journal + ["-b"] + session,
        journal + ["-b", "-1"] + session,
        journal + ["-b", "-k"],
        ["findmnt", "/srv/raspi-player"],
        ["kmsprint"],
        ["vcgencmd", "get_throttled"],
        *(user_commands(uid) if uid is not None else []),
    ]


def save_report(directory: Path, report: str) -> None:
    """Replace the latest report only after the bounded new file is complete."""
    latest = directory / "raspi-diagnostics.txt"
    temporary = directory / "raspi-diagnostics.tmp"
    with temporary.open("wb") as stream:
        stream.write(report.encode("utf-8")[:REPORT_LIMIT])
        stream.flush()
        os.fsync(stream.fileno())
    if latest.exists():
        latest.replace(directory / "raspi-diagnostics-previous.txt")
    temporary.replace(latest)


def main() -> None:
    import pwd

    print("DIAGNOSTICS_BEGIN: collecting boot and player state", flush=True)
    report = f"Raspi Player diagnostics: {datetime.now(UTC).isoformat()}\n"
    try:
        user = pwd.getpwnam("player")
    except KeyError:
        user = None
        report += "ERROR: player account is missing; collecting system state.\n"
    report += "".join(
        capture(command) for command in commands(user.pw_uid if user else None)
    )
    report += display_state(Path("/sys/class/drm"))
    for path in (
        Path(user.pw_dir if user else "/home/player") / ".xsession-errors",
        Path("/var/log/lightdm/lightdm.log"),
    ):
        report += file_tail(path)
    save_report(BOOT, report)
    print("DIAGNOSTICS_COMPLETE: report saved", flush=True)


if __name__ == "__main__":
    main()
