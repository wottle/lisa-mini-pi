#!/usr/bin/env bash
# Installs splash.png as the Raspberry Pi OS boot splash, replacing the
# stock Plymouth "pix" theme's image. Must be run with sudo (writes into
# /usr/share/plymouth, root-owned) - see ../../docs/software-setup.md
# for the full writeup of why "pix" specifically and how the image gets
# scaled/centered at boot.
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_DIR="/usr/share/plymouth/themes/pix"
DEST="$THEME_DIR/splash.png"
BACKUP="$THEME_DIR/splash.png.orig"

if [ ! -d "$THEME_DIR" ]; then
  echo "error: $THEME_DIR not found - is the 'pix' Plymouth theme installed?" >&2
  exit 1
fi

if [ ! -f "$BACKUP" ]; then
  cp "$DEST" "$BACKUP"
  echo "backed up stock splash to $BACKUP"
else
  echo "backup already exists at $BACKUP, leaving it alone"
fi

cp "$SCRIPT_DIR/splash.png" "$DEST"
echo "installed $SCRIPT_DIR/splash.png -> $DEST"

# Plymouth needs "splash" (and normally "quiet", to suppress the kernel/
# systemd boot text this is meant to cover up) on the kernel command
# line to engage at all - confirmed on real hardware (2026-09-27) that
# without it, boot just shows raw text instead of this custom splash,
# even with the image/theme correctly installed above. Also adds
# plymouth.ignore-serial-consoles: Plymouth disables its graphical splash
# whenever it detects a serial console (cmdline.txt's default
# "console=serial0,115200"), which is otherwise a sensible default for a
# headless Pi but wrong for this kiosk. Idempotent - only appends
# whichever of these three tokens aren't already present.
CMDLINE="/boot/firmware/cmdline.txt"
if [ -f "$CMDLINE" ]; then
  for token in splash quiet plymouth.ignore-serial-consoles; do
    if ! grep -q "$token" "$CMDLINE"; then
      sed -i "s/\$/ $token/" "$CMDLINE"
      echo "added '$token' to $CMDLINE"
    fi
  done
else
  echo "warning: $CMDLINE not found - add 'splash quiet plymouth.ignore-serial-consoles' to your kernel command line by hand, or Plymouth won't show this splash" >&2
fi

update-initramfs -u
echo "initramfs updated - reboot to see the new splash"
