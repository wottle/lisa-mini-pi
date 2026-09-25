#!/usr/bin/env bash
# provision.sh - Automates the Lisa Mini Pi software setup on a fresh
# Raspberry Pi OS (64-bit, "trixie") install.
#
# WHAT THIS SCRIPT DOES: installs/builds every emulator, the kiosk
# launcher, the GPIO power-button/LED plumbing, systemd units, the
# polkit rule, and (optionally) the boot splash - everything currently
# spread across docs/software-setup.md and software/lisa-pi-launcher/
# SETUP.md, automated into one idempotent pass.
#
# WHAT THIS SCRIPT DELIBERATELY DOES NOT DO: place any ROM or OS disk
# image. Every one of those is copyrighted and this project has never
# redistributed them - see "not redistributed here" throughout the docs
# above. You must legally source your own and drop them into the paths
# this script prints at the end. This is also why there is no
# "pre-packaged SD card image" for this project: an image with those
# assets baked in would be a real copyright problem, not just a style
# choice.
#
# USAGE: read this script before running it, like any script that
# invokes sudo. It's meant to be run interactively by you, on the Pi
# itself, over SSH or at the console - not by an automated agent.
#
#   ./provision.sh                 # install everything (Lisa, Basilisk
#                                   # II, Mini vMac, Previous, LinApple)
#   ./provision.sh --skip-next --skip-apple2
#                                   # skip Previous/LinApple - the
#                                   # project's own Pi 3B doesn't have
#                                   # the RAM/performance headroom for
#                                   # them (see docs/software-setup.md's
#                                   # Pi 3B note); this script warns and
#                                   # suggests this automatically on a
#                                   # <2GB-RAM machine, but never decides
#                                   # for you.
#   ./provision.sh --skip-boot-splash
#                                   # skip the custom boot splash/rainbow
#                                   # screen changes (cosmetic only)
#
# Safe to re-run: every step checks for existing work first and skips
# it, so an interrupted run (or a deliberate second pass after fixing
# something) doesn't redo completed steps or duplicate config.
#
# Version pins (wxWidgets 3.2.1, Previous 4.4-0wmlive1, LinApple
# v3.0-beta-3) match what docs/software-setup.md documents as
# known-working as of 2026-09-25 - like the docs themselves, these will
# go stale as newer releases ship. Check docs/software-setup.md §6-7 for
# current download URLs if a step 404s.
set -euo pipefail

SKIP_NEXT=0
SKIP_APPLE2=0
SKIP_BOOT_SPLASH=0
for arg in "$@"; do
  case "$arg" in
    --skip-next) SKIP_NEXT=1 ;;
    --skip-apple2) SKIP_APPLE2=1 ;;
    --skip-boot-splash) SKIP_BOOT_SPLASH=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^#//'
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg (see --help)" >&2
      exit 1
      ;;
  esac
done

step() { echo; echo "==> $*"; }
skip() { echo "    already done, skipping: $*"; }

if [ "$(id -u)" -eq 0 ]; then
  echo "Run this as your normal user, not root - it calls sudo itself where needed." >&2
  exit 1
fi

TOTAL_RAM_KB="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
if [ "$TOTAL_RAM_KB" -gt 0 ] && [ "$TOTAL_RAM_KB" -lt 2097152 ] && { [ "$SKIP_NEXT" -eq 0 ] || [ "$SKIP_APPLE2" -eq 0 ]; }; then
  echo
  echo "This machine has under 2GB RAM (Pi 3B territory). The project's own"
  echo "Pi 3B doesn't get Previous/LinApple installed - not enough headroom"
  echo "on top of LisaEm/Basilisk II/Mini vMac (see docs/software-setup.md's"
  echo "Pi 3B note). Consider re-running with --skip-next --skip-apple2."
  read -rp "Continue installing all five anyway? [y/N] " REPLY
  [ "$REPLY" = "y" ] || [ "$REPLY" = "Y" ] || exit 1
fi

# ---------------------------------------------------------------------
step "1. Base packages"
# ---------------------------------------------------------------------
sudo apt update
sudo apt install -y \
  git build-essential curl \
  python3-pip python3-venv python3-pygame python3-pil \
  basilisk2 \
  openbox xserver-xorg xinit x11-xserver-utils libx11-dev x11-utils \
  libgtk-3-dev \
  gpiod

# ---------------------------------------------------------------------
step "2. GPIO pin state (LED off, button input with pull-down)"
# ---------------------------------------------------------------------
pinctrl set 18 op dl
pinctrl set 17 ip pd

# ---------------------------------------------------------------------
step "3. wxWidgets 3.2.1 (GTK), needed by LisaEm"
# ---------------------------------------------------------------------
# The upstream LisaEm project's own scripts/build-wx3.2.1-gtk.sh, adapted
# for a single fixed version/target rather than its multi-version loop -
# this project's SETUP.md had never actually captured this before.
WX_PREFIX=/usr/local/wx3.2.1-gtk
if [ -x "$WX_PREFIX/bin/wx-config" ]; then
  skip "wxWidgets 3.2.1 (found $WX_PREFIX/bin/wx-config)"
else
  mkdir -p ~/wx-build
  cd ~/wx-build
  if [ ! -d wxWidgets-3.2.1 ]; then
    curl -L https://github.com/wxWidgets/wxWidgets/releases/download/v3.2.1/wxWidgets-3.2.1.tar.bz2 \
      -o wxWidgets-3.2.1.tar.bz2
    tar xjf wxWidgets-3.2.1.tar.bz2
  fi
  cd wxWidgets-3.2.1
  rm -rf build-gtk
  mkdir build-gtk
  cd build-gtk
  CFLAGS="-fPIC" CXXFLAGS="-fPIC" ../configure \
    --with-gtk --enable-unicode --disable-debug --disable-shared \
    --without-expat --disable-richtext \
    --with-libpng=builtin --with-libjpeg=builtin --with-libtiff=builtin --with-libxpm=builtin \
    --prefix="$WX_PREFIX"
  make -j"$(nproc)"
  sudo make install
fi
export PATH="$WX_PREFIX/bin:$PATH"

# ---------------------------------------------------------------------
step "4. LisaEm (wottle/lisaem, lisa-fixes-1024x768 branch)"
# ---------------------------------------------------------------------
LISAEM_DIR=~/lisaem-fixes-src
if [ -x "$LISAEM_DIR/bin/lisaem" ]; then
  skip "LisaEm (found $LISAEM_DIR/bin/lisaem)"
else
  if [ ! -d "$LISAEM_DIR" ]; then
    git clone --branch lisa-fixes-1024x768 https://github.com/wottle/lisaem.git "$LISAEM_DIR"
  fi
  ( cd "$LISAEM_DIR" && PATH="$WX_PREFIX/bin:$PATH" ./build.sh clean build )
fi

# ---------------------------------------------------------------------
step "5. Mini vMac (erichelgeson/minivmac fork)"
# ---------------------------------------------------------------------
MINIVMAC_SRC=~/minivmac-erich
MINIVMAC_FINAL=~/minivmac-final
if [ -x "$MINIVMAC_FINAL/minivmac" ]; then
  skip "Mini vMac (found $MINIVMAC_FINAL/minivmac)"
else
  if [ ! -d "$MINIVMAC_SRC" ]; then
    git clone https://github.com/erichelgeson/minivmac.git "$MINIVMAC_SRC"
  fi
  (
    cd "$MINIVMAC_SRC"
    gcc -o setup_t setup/tool.c
    ./setup_t -t xgen -cpu x64 -m II -ndp 1 -fullscreen 1 \
      -hres 512 -vres 342 -mf 2 -magnify 1 > setup.sh
    bash setup.sh
    mkdir -p bld
    # this fork's generated Makefile is missing include paths - see
    # SETUP.md §5 for why.
    sed -i 's/mk_COptions = -c$/mk_COptions = -c -g -Icfg\/ -Isrc\//' Makefile
    make
  )
  mkdir -p "$MINIVMAC_FINAL"
  cp "$MINIVMAC_SRC/minivmac" "$MINIVMAC_FINAL/minivmac"
fi

# ---------------------------------------------------------------------
if [ "$SKIP_NEXT" -eq 0 ]; then
step "6. Previous (NeXT emulator)"
# ---------------------------------------------------------------------
if dpkg -s previous >/dev/null 2>&1; then
  skip "Previous (dpkg already has it installed)"
else
  TMP_DEB=/tmp/previous_arm64.deb
  curl -L -o "$TMP_DEB" http://previous.nextcommunity.net/release/previous_4.4-0wmlive1_arm64.deb
  sudo apt-get install -y "$TMP_DEB"
fi
else
  step "6. Previous (NeXT emulator) - skipped (--skip-next)"
fi

# ---------------------------------------------------------------------
if [ "$SKIP_APPLE2" -eq 0 ]; then
step "7. LinApple (Apple II emulator) + Total Replay"
# ---------------------------------------------------------------------
if dpkg -s linapple >/dev/null 2>&1; then
  skip "LinApple (dpkg already has it installed)"
else
  TMP_DEB=/tmp/linapple_arm64.deb
  curl -L -o "$TMP_DEB" \
    https://github.com/linappleii/linapple/releases/download/v3.0-beta-3/linapple-v3.0-beta-3-linux-arm64.deb
  sudo apt-get install -y "$TMP_DEB"
fi

# Two real packaging bugs in this beta's arm64 .deb on Debian trixie -
# see docs/software-setup.md §7 for the full explanation of each.
sudo apt-get install -y libsdl3-image0
LIBZIP_SO="$(find /usr/lib -maxdepth 2 -name 'libzip.so.5.*' 2>/dev/null | sort -V | tail -1)"
if [ -n "$LIBZIP_SO" ] && [ ! -e /usr/lib/aarch64-linux-gnu/libzip.so.4 ]; then
  sudo ln -sf "$LIBZIP_SO" /usr/lib/aarch64-linux-gnu/libzip.so.4
  sudo ldconfig
fi
if command -v linapple >/dev/null 2>&1 && ldd "$(command -v linapple)" | grep -q "not found"; then
  echo "WARNING: linapple still has unresolved libraries - check manually:" >&2
  ldd "$(command -v linapple)" | grep "not found" >&2
fi

TOTAL_REPLAY=~/TotalReplay_v6.1.hdv
if [ -f "$TOTAL_REPLAY" ]; then
  skip "Total Replay disk image (found $TOTAL_REPLAY)"
else
  curl -L -o "$TOTAL_REPLAY" "https://archive.org/download/TotalReplay/Total%20Replay%20v6.1.hdv"
fi
else
  step "7. LinApple (Apple II emulator) - skipped (--skip-apple2)"
fi

# ---------------------------------------------------------------------
step "8. The kiosk launcher itself"
# ---------------------------------------------------------------------
LAUNCHER_REPO=~/lisa-mini-pi
if [ -d "$LAUNCHER_REPO/.git" ]; then
  skip "launcher repo (found $LAUNCHER_REPO)"
else
  git clone https://github.com/wottle/lisa-mini-pi.git "$LAUNCHER_REPO"
fi
LAUNCHER_DIR="$LAUNCHER_REPO/software/lisa-pi-launcher"
( cd "$LAUNCHER_DIR" && python3 gen_icons.py )

# ---------------------------------------------------------------------
step "9. Openbox kiosk session config"
# ---------------------------------------------------------------------
mkdir -p ~/.config/openbox
if [ -f ~/.config/openbox/rc.xml ] && grep -q 'class="\*"' ~/.config/openbox/rc.xml 2>/dev/null; then
  skip "openbox rc.xml (undecorated-window rule already present)"
else
  cp /etc/xdg/openbox/rc.xml ~/.config/openbox/rc.xml
  # Insert the "no titlebar on any window" rule just before </applications>,
  # matching SETUP.md §7 - matches this kiosk's no-window-manager look.
  python3 - <<'PYEOF'
import pathlib
path = pathlib.Path.home() / ".config/openbox/rc.xml"
text = path.read_text()
rule = '  <application class="*">\n    <decor>no</decor>\n  </application>\n'
text = text.replace("</applications>", rule + "</applications>")
path.write_text(text)
PYEOF
fi

# ---------------------------------------------------------------------
step "10. systemd units + polkit rule (sudo)"
# ---------------------------------------------------------------------
SYSTEM_DIR="$LAUNCHER_DIR/system"
sudo cp "$SYSTEM_DIR/launcher.service" "$SYSTEM_DIR/launcher-watchdog.service" \
  "$SYSTEM_DIR/launcher-watchdog.timer" /etc/systemd/system/
sudo cp "$SYSTEM_DIR/10-lisa-launcher-power.rules" /etc/polkit-1/rules.d/
sudo systemctl daemon-reload
sudo systemctl disable --now lightdm 2>/dev/null || true
sudo systemctl enable --now launcher.service launcher-watchdog.timer

# ---------------------------------------------------------------------
if [ "$SKIP_BOOT_SPLASH" -eq 0 ]; then
step "11. Custom boot splash + disabling the rainbow firmware screen"
# ---------------------------------------------------------------------
BOOT_SPLASH_DIR="$LAUNCHER_REPO/software/boot-splash"
if [ -x "$BOOT_SPLASH_DIR/install.sh" ]; then
  sudo "$BOOT_SPLASH_DIR/install.sh"
fi
CONFIG_TXT=/boot/firmware/config.txt
if [ -w "$CONFIG_TXT" ] || sudo test -w "$CONFIG_TXT"; then
  if grep -q '^disable_splash=1' "$CONFIG_TXT" 2>/dev/null; then
    skip "disable_splash=1 (already in $CONFIG_TXT)"
  else
    sudo sed -i '/^arm_boost=1$/a disable_splash=1' "$CONFIG_TXT"
  fi
fi
else
  step "11. Custom boot splash - skipped (--skip-boot-splash)"
fi

# ---------------------------------------------------------------------
step "Done - manual steps still needed"
# ---------------------------------------------------------------------
cat <<EOF

Everything installable without copyrighted assets is now in place. You
still need to, at minimum:

  1. Place your own legally-obtained ROM/disk files:
       Lisa:       ~/boot.ROM, ~/lisaem-widget.dc42
       Basilisk II: edit ~/.config/BasiliskII/prefs (created on
                    Basilisk II's first run) to point at your Mac ROM
                    and a classic Mac OS disk image
       Mini vMac:  ~/minivmac-final/MacII.ROM, ~/minivmac-final/System6.image
EOF
if [ "$SKIP_NEXT" -eq 0 ]; then
cat <<EOF
       Previous:   your own NeXTSTEP disk image (path is chosen during
                   its one-time interactive setup, step 3 below)
EOF
fi
cat <<EOF
     Edit config.json in $LAUNCHER_DIR if you place any of these
     somewhere other than the paths above.

  2. Wire the physical GPIO power button/LED (see
     docs/software-setup.md §2): GPIO18 (pin 12) -> LED -> GND (e.g.
     pin 14); 3.3V (pin 1 or 17) -> resistor -> switch -> GPIO17 (pin 11).
EOF
if [ "$SKIP_NEXT" -eq 0 ]; then
cat <<EOF

  3. One-time interactive Previous setup (needs a keyboard at the Pi) -
     see docs/software-setup.md §6 for the exact settings (Machine Type,
     Boot Options, SCSI Disk, Save config) and the "Show at startup"
     gotcha.
EOF
fi
cat <<EOF

  4. Reboot, and confirm it boots straight into the picker.

EOF
