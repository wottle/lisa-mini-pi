#!/usr/bin/env bash
# Launches LisaEm: lights the power LED (GPIO18) while it runs, and turns
# it off once LisaEm exits, however it exits (clean shutdown, crash, or
# Ctrl+C). The GPIO power-button watcher runs independently of this
# script (started once at boot) - see lisa-power-button-watcher.sh.
#
# Forces the X11 GDK backend: without this, GTK prefers native Wayland
# when WAYLAND_DISPLAY is set (even with DISPLAY also set), which makes
# LisaEm's window invisible to X11 tools like xdotool (used by the watcher).
set -euo pipefail

LISAEM_BIN="${LISAEM_BIN:-$HOME/lisaem-fixes-src/bin/lisaem}"
LED_PIN=18
LOG="$HOME/lisa-run-with-led.log"

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
log "LED on - starting LisaEm ($LISAEM_BIN)"

# Temporary diagnostic: polls which window actually has X input focus
# while LisaEm runs, for tracking down the mouse-click-launch focus bug
# (see x11focus.py). Logs to a separate file so it's easy to strip back
# out once that's resolved.
FOCUS_LOG="$HOME/lisa-focus-diag.log"
(
  for _ in $(seq 1 30); do
    sleep 1
    {
      echo "--- $(date '+%H:%M:%S.%N') ---"
      DISPLAY=:0 xdotool getactivewindow getwindowname 2>&1
      DISPLAY=:0 xdotool getactivewindow getwindowpid 2>&1
    } >> "$FOCUS_LOG" 2>&1
  done
) &
FOCUS_DIAG_PID=$!

GDK_BACKEND=x11 "$LISAEM_BIN" "$@"
log "LisaEm exited"
kill "$FOCUS_DIAG_PID" 2>/dev/null || true
