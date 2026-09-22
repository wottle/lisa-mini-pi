#!/bin/sh
# The desktop-side half of launcher.py's Q key: returns from the full
# Raspberry Pi Desktop back to the kiosk. Starting launcher.service would
# auto-stop lightdm.service via launcher.service's Conflicts=, doing both
# in one systemd transaction - but on real hardware (Pi 4 + the project's
# 1024x768 HDMI panel) that back-to-back CRTC teardown/setup reliably
# triggers a kernel bug (WARNING in drivers/gpu/drm/vc4/vc4_hvs.c,
# __vc4_hvs_stop_channel, hit via the outgoing Xorg's FBIOBLANK ioctl on
# exit) that leaves the display flickering blue/black until the new X
# session gives up. Explicitly stopping lightdm first and pausing before
# starting the kiosk gives the outgoing Xorg's teardown time to fully
# settle before the new CRTC commit happens - this is a workaround for a
# kernel/GPU-driver issue, not a real fix; revisit once an upstream
# kernel update addresses it (see docs/software-setup.md).
systemctl start launcher-watchdog.timer
systemctl stop lightdm.service
sleep 2
systemctl start launcher.service
