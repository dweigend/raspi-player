#!/bin/bash
# Preserve first-boot errors on the readable boot volume and the boot console.
set -euo pipefail
/usr/bin/python3 /boot/firmware/player/provision.py 2>&1 | tee /boot/firmware/raspi-setup.txt
