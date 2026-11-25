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
#
# F12 closes GSplus, as it does LisaEm and LinApple. GSplus itself has no quit
# key (plain F12 does nothing in it), so while it runs this wrapper also runs
# xbindkeys with F12 bound to the same window close the power button uses
# (`wmctrl -x -c gsplus.gsplus`). It is a global key grab, so it exists only
# for the length of the GSplus session and is stopped when GSplus exits:
# otherwise it would swallow the F12 that LisaEm and LinApple need. Without
# xbindkeys installed GSplus still runs, just without the F12 quit.
#
# Its standard input is detached too (</dev/null). GSplus has a debugger
# console with a thread that reads stdin, and launcher.service gives its
# children a terminal as stdin. With the terminal attached, closing GSplus's
# window closed it on screen but the process never finished shutting down, so
# the picker never came back. (Found on the Pi 5, 2026-11-25.)
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

KEYS_PID=""
KEYS_CFG=""
cleanup() {
  [ -n "$KEYS_PID" ] && kill "$KEYS_PID" 2>/dev/null || true
  [ -n "$KEYS_CFG" ] && rm -f "$KEYS_CFG"
  turn_off_led
}
trap cleanup EXIT

log "script start, args: $*"
pinctrl set "$LED_PIN" op dh 2>/dev/null || true
log "LED on - starting GSplus ($GSPLUS_BIN)"
cd "$GSPLUS_DIR"
if command -v xbindkeys >/dev/null 2>&1; then
  KEYS_CFG="$(mktemp)"
  printf '%s\n' '"wmctrl -x -c gsplus.gsplus"' '  F12' > "$KEYS_CFG"
  DISPLAY="${DISPLAY:-:0}" xbindkeys -f "$KEYS_CFG" -n >/dev/null 2>&1 &
  KEYS_PID=$!
  log "F12 closes GSplus (xbindkeys pid $KEYS_PID)"
  sleep 0.3   # give it a moment to take the key grab before GSplus starts
fi
status=0
"$GSPLUS_BIN" -cfg "$GSPLUS_CFG" "$@" </dev/null >/dev/null 2>&1 || status=$?
log "GSplus exited (status $status)"
exit "$status"
