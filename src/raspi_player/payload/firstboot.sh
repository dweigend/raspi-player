#!/bin/sh
# Run the offline Python provisioner on first boot; failures remain visible.
set -eu
exec /usr/bin/python3 /boot/firmware/player/provision.py
