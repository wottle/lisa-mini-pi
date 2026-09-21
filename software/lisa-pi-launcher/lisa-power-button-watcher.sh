#!/usr/bin/env bash
# Persistent power-button watcher: meant to run continuously for the whole
# time the Pi is on (started once at boot alongside the launcher's X
# session), not just while LisaEm is running.
#
# On each GPIO17 press:
#   - If LisaEm is already running, send it F12 (its power-button
#     shortcut) to shut it down.
#   - If LisaEm is not running (the launcher menu is showing), launch it
#     via lisa-run-with-led.sh instead, i.e. the button "powers on" the
#     Lisa the same way a real one would.
set -uo pipefail

LISAEM_MATCH="bin/lisaem"
RUN_SCRIPT="${RUN_SCRIPT:-$HOME/lisa-run-with-led.sh}"
RUN_ARGS=(-p -d -F -q)

echo "Watching GPIO17 for power-button presses (Ctrl+C to stop)..."
gpiomon --bias=pull-down --edges=rising --debounce-period=20ms --chip=gpiochip0 17 | while read -r _; do
  if pgrep -f "$LISAEM_MATCH" >/dev/null 2>&1; then
    echo "power button pressed - LisaEm is running, sending F12"
    DISPLAY=:0 xdotool key --clearmodifiers F12
  else
    echo "power button pressed - LisaEm is not running, powering on"
    "$RUN_SCRIPT" "${RUN_ARGS[@]}" &
  fi
done
