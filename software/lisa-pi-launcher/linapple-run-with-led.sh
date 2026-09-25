#!/usr/bin/env bash
# Launches LinApple: lights the power LED (GPIO18) while it runs, and
# turns it off once it exits, however it exits (F12 quit, crash, or
# Ctrl+C). Mirrors lisa-run-with-led.sh's LED handling for LisaEm - the
# GPIO power-button watcher sends LinApple F12 while it's running (see
# lisa-power-button-watcher.sh), and this LED is the visual signal to the
# user that the button will do something.
set -euo pipefail

LINAPPLE_BIN="${LINAPPLE_BIN:-/usr/bin/linapple}"
LED_PIN=18
LOG="$HOME/linapple-run-with-led.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
}

turn_off_led() {
  pinctrl set "$LED_PIN" dl >/dev/null 2>&1 || true
  log "LED off"
}
trap turn_off_led EXIT

log "script start, args: $*"
pinctrl set "$LED_PIN" op dh
log "LED on - starting LinApple ($LINAPPLE_BIN)"
"$LINAPPLE_BIN" "$@"
log "LinApple exited"
