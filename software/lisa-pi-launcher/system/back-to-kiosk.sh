#!/bin/sh
# The desktop-side half of launcher.py's Q key: returns from the full
# Raspberry Pi Desktop back to the kiosk. Starting launcher.service
# auto-stops lightdm.service via launcher.service's Conflicts=, so this
# just needs to also restart the watchdog timer that Q suppressed on the
# way out.
systemctl start launcher-watchdog.timer
systemctl start launcher.service
