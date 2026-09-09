#!/bin/sh
# Record early boot and LightDM entry directly on bootfs without a GUI.
# Keep the previous marker and at most 64 KiB of the preceding boot's journal.
set -u
stage=${1:-lightdm}
report=/boot/firmware/raspi-boot.txt
if [ "$stage" = early ]; then
    report=/boot/firmware/raspi-early-boot.txt
fi
if [ -f "$report" ]; then
    cp "$report" "${report%.txt}-previous.txt"
fi
exec > "$report" 2>&1
echo "BOOT_CHECK: $stage reached"
date -Is
cat /proc/cmdline
echo 'CURRENT BOOT: pending systemd jobs'
timeout 5 systemctl list-jobs --no-pager
echo 'PREVIOUS BOOT: session, player and diagnostic errors'
timeout 5 journalctl -b -1 --no-pager -n 150 \
    _SYSTEMD_UNIT=lightdm.service + _SYSTEMD_USER_UNIT=raspi-player.service + \
    SYSLOG_IDENTIFIER=raspi-session + _SYSTEMD_UNIT=raspi-diagnostics.service \
    2>&1 | tail -c 65536
echo "BOOT_CHECK: $stage complete"
sync -f "$report"
