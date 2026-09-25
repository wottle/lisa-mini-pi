#!/usr/bin/env bash
# Launches Previous: lights the power LED (GPIO18) while it runs, and
# turns it off once it exits, however it exits (clean shutdown via F10,
# crash, or Ctrl+C). Mirrors lisa-run-with-led.sh's LED handling for
# LisaEm - the GPIO power-button watcher sends Previous F10 while it's
# running (see lisa-power-button-watcher.sh), and this LED is the visual
# signal to the user that the button will do something.
set -euo pipefail

PREVIOUS_BIN="${PREVIOUS_BIN:-/usr/bin/previous}"
LED_PIN=18
LOG="$HOME/previous-run-with-led.log"

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
log "LED on - starting Previous ($PREVIOUS_BIN)"
"$PREVIOUS_BIN" "$@"
log "Previous exited"
