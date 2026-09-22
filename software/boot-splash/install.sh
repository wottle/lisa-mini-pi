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

update-initramfs -u
echo "initramfs updated - reboot to see the new splash"
