#!/usr/bin/env bash
# Switch the kiosk between the default 1024x768 output and the iPad 3/4
# panel's native 2048x1536.
#
#   display-mode.sh native   panel native; launcher draws 2x; Basilisk II
#                            upscales with crisp nearest-neighbour; LisaEm
#                            hidpi_scale=200
#   display-mode.sh 1024     the default: Pi outputs 1024x768@60, the panel's
#                            controller upscales; hidpi_scale=100
#   display-mode.sh status   show what is set now
#
# What it changes (all under $HOME, no sudo): a marker file that
# system/xsession-launcher.sh checks before it runs xrandr, two lines in
# ~/.config/BasiliskII/prefs (scale_nearest, scale_integer) and hidpi_scale
# and the window size in ~/.lisaem. Originals are saved once as *.bak-displaymode.
# It takes effect after the kiosk restarts:  sudo systemctl restart launcher
# Mini vMac is built at a fixed 1024x684 and is not changed by this.
set -euo pipefail

MARK="$HOME/.config/lisa-launcher/native-resolution"
B2="$HOME/.config/BasiliskII/prefs"
LISA="$HOME/.lisaem"

backup() { [ -f "$1" ] && [ ! -f "$1.bak-displaymode" ] && cp -p "$1" "$1.bak-displaymode" || true; }
b2_set() { grep -qE "^$1 " "$B2" && sed -i -E "s/^$1 .*/$1 $2/" "$B2" || echo "$1 $2" >> "$B2"; }
b2_del() { sed -i -E "/^$1 /d" "$B2"; }
lisa_scale() { sed -i -E "s/^hidpi_scale=.*/hidpi_scale=$1/" "$LISA"; }
# LisaEm rewrites its window size to the screen size when it runs, so set it too
lisa_size() { sed -i -E "s/^sizex=.*/sizex=$1/; s/^sizey=.*/sizey=$2/" "$LISA"; }

status() {
  if [ -e "$MARK" ]; then echo "kiosk mode : native 2048x1536 (marker present)"
  else echo "kiosk mode : 1024x768@60 (default)"; fi
  [ -f "$B2" ]   && echo "Basilisk II: $(grep -E '^(frameskip|scale_nearest|scale_integer) ' "$B2" | tr '\n' ';')"
  [ -f "$LISA" ] && echo "LisaEm     : $(grep -E '^hidpi_scale=' "$LISA")"
  [ -n "${DISPLAY:-}" ] && command -v xrandr >/dev/null && echo "X right now: $(xrandr 2>/dev/null | grep -o '[0-9]*x[0-9]*+0+0' | head -1)"
  true
}

case "${1:-status}" in
  native|1024)
    if [ -f "$LISA" ] && pgrep -x lisaem >/dev/null 2>&1; then
      echo "LisaEm is running; it rewrites ~/.lisaem on exit. Close it and run again." >&2; exit 1
    fi
    backup "$B2"; backup "$LISA"
    if [ "$1" = native ]; then
      mkdir -p "$(dirname "$MARK")"; touch "$MARK"
      [ -f "$B2" ] && { b2_set scale_nearest true; b2_set scale_integer true; }
      [ -f "$LISA" ] && { lisa_scale 200; lisa_size 2048 1536; }
    else
      rm -f "$MARK"
      [ -f "$B2" ] && { b2_del scale_nearest; b2_del scale_integer; }
      [ -f "$LISA" ] && { lisa_scale 100; lisa_size 1024 768; }
    fi
    status
    echo "Now restart the kiosk to apply:  sudo systemctl restart launcher"
    ;;
  status) status ;;
  *) echo "usage: $0 native | 1024 | status" >&2; exit 2 ;;
esac
