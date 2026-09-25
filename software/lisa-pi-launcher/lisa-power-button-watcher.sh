#!/usr/bin/env bash
# Persistent power-button watcher: meant to run continuously for the whole
# time the Pi is on (started once at boot alongside the launcher's X
# session), not just while LisaEm is running.
#
# On each GPIO17 press, dispatches to whichever emulator is currently
# running - each one's shutdown trigger was individually verified (source
# review and/or live testing, not guessed) to be a real clean-shutdown
# path, not a kill:
#   - LisaEm: F12, its power-button hotkey (see software-setup.md §1).
#   - Previous: F10, its documented clean-shutdown key (software-setup.md
#     §6), same as pressing it manually inside NeXTSTEP.
#   - Basilisk II, Mini vMac, and LinApple: deliberately NOT handled, just
#     ignored if the button is pressed while any of them is running.
#     Mini vMac (this fork) has no safe host-triggerable shutdown at all -
#     no signal handler, buffered disk writes only flushed on a clean
#     exit, and its own force-quit path (Ctrl+Q+Y) is documented by the
#     emulator itself as a disk-corruption risk. Basilisk II's upstream
#     source maps a window-close request to a clean ADB Power keypress,
#     but this specific Debian-packaged build (confirmed 2026-09-24: both
#     `xdotool windowclose` and a raw WM_DELETE_WINDOW ClientMessage sent
#     directly to its actual window had zero effect on real hardware) has
#     no working equivalent - shut both of these down from inside the
#     guest instead. Apple II/LinApple has no soft-power concept to
#     trigger, same as real Apple II hardware.
#   - Nothing running (the launcher menu is showing): power on the Lisa
#     via lisa-run-with-led.sh, i.e. the button "powers on" the Lisa the
#     same way a real one would.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RUN_SCRIPT="${RUN_SCRIPT:-$SCRIPT_DIR/lisa-run-with-led.sh}"
# Matches the launcher's own config.json invocation (-k implies -p -d -F
# plus quit-on-poweroff). No -M/-M- flag: the lisa-fixes-1024x768 branch
# doesn't register one at all - see this project's SETUP.md Known Gaps for
# how mouse-to-top-menu is instead kept on via a source patch. Using -M-
# here would make LisaEm reject the whole command line.
RUN_ARGS=(-k -d)

echo "Watching GPIO17 for power-button presses (Ctrl+C to stop)..."
gpiomon --bias=pull-down --edges=rising --debounce-period=20ms --chip=gpiochip0 17 | while read -r _; do
  if pgrep -f "bin/lisaem" >/dev/null 2>&1; then
    echo "power button pressed - LisaEm is running, sending F12"
    DISPLAY=:0 xdotool key --clearmodifiers F12
  elif pgrep -x previous >/dev/null 2>&1; then
    echo "power button pressed - Previous is running, sending F10"
    DISPLAY=:0 xdotool key --clearmodifiers F10
  elif pgrep -x BasiliskII >/dev/null 2>&1 || pgrep -x minivmac >/dev/null 2>&1 || pgrep -x linapple >/dev/null 2>&1; then
    echo "power button pressed - Basilisk II/Mini vMac/LinApple is running, no safe host-side shutdown trigger exists - ignoring"
  else
    echo "power button pressed - nothing is running, powering on Lisa"
    "$RUN_SCRIPT" "${RUN_ARGS[@]}" &
  fi
done
