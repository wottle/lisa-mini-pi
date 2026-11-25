#!/usr/bin/env bash
# Launches GSplus (Apple IIgs): lights the power LED (GPIO18) while it runs
# and turns it off once it exits, however it exits. Mirrors
# linapple-run-with-led.sh. The GPIO power-button watcher closes GSplus by
# sending Alt+F4 to the window manager (GSplus has no quit key of its own;
# a window close is a clean quit), and this LED is the visual signal that the
# button will do something.
#
# The ROM and disk come in as arguments from config.json, e.g.
#   gsplus-run-with-led.sh -rom ~/ROM.01 -s7d1 ~/gsos.hdv
# Display settings (fullscreen, status line off) live in ~/gsplus/config.kegs,
# which provision.sh seeds.
#
# GSplus's stdout/stderr are thrown away on purpose: when the emulated
# machine touches hardware GSplus does not implement it prints a line per
# access, which measured about 400 MB of log in one minute.
set -euo pipefail

GSPLUS_DIR="${GSPLUS_DIR:-$HOME/gsplus}"
GSPLUS_BIN="${GSPLUS_BIN:-$GSPLUS_DIR/gsplus}"
GSPLUS_CFG="${GSPLUS_CFG:-$GSPLUS_DIR/config.kegs}"
LED_PIN=18
LOG="$HOME/gsplus-run-with-led.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
}

turn_off_led() {
  pinctrl set "$LED_PIN" dl >/dev/null 2>&1 || true
  log "LED off"
}
trap turn_off_led EXIT

log "script start, args: $*"
pinctrl set "$LED_PIN" op dh 2>/dev/null || true
log "LED on - starting GSplus ($GSPLUS_BIN)"
cd "$GSPLUS_DIR"
"$GSPLUS_BIN" -cfg "$GSPLUS_CFG" "$@" >/dev/null 2>&1
log "GSplus exited"
