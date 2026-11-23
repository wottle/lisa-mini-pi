#!/bin/sh
# Started by launcher.service inside a minimal X session (no desktop, no
# panel). A bare X11 session with no window manager at all does not
# reliably hand keyboard input focus to a newly-mapped window - that was
# causing the picker to lose keyboard input after an emulator closed, and
# an emulator to never receive keyboard input when launched.
#
# Openbox brokers that focus handoff correctly (unlike matchbox, which was
# tried first: it fixed focus but doesn't properly implement EWMH
# _NET_WM_STATE_FULLSCREEN, so LisaEm's F11 leave-fullscreen toggled its
# internal state but the window never actually resized). Openbox is still
# lightweight/kiosk-appropriate (no panel, no desktop icons) but is a
# mature, correctly-EWMH-compliant WM - every emulator here relies on the
# same fullscreen/focus behavior, not just LisaEm.
# ~/.config/openbox/rc.xml forces decor="no" on every window so it stays
# invisible/chromeless, matching the no-window-manager look.
openbox &

# Drive the panel at 1024x768@60 and let the LCD controller board upscale it
# to the iPad 3/4 panel's native 2048x1536. The Pi pushes a quarter of the
# pixels and every emulator (all set up for 1024x768) renders 1:1 with no
# software scaling. Picks whichever output is connected instead of
# hard-coding HDMI-2; if the mode is not offered this is a harmless no-op and
# the launcher just scales its layout to whatever size X came up at.
# To use the panel's native mode instead, run scripts/display-mode.sh native
# (it creates the marker file checked below, and adjusts Basilisk II and
# LisaEm to match); scripts/display-mode.sh 1024 undoes it.
if [ ! -e "$HOME/.config/lisa-launcher/native-resolution" ]; then
  OUT=$(xrandr 2>/dev/null | awk '/ connected/{print $1; exit}')
  [ -n "$OUT" ] && xrandr --output "$OUT" --mode 1024x768 --rate 60 2>/dev/null || true
fi

cd "$(dirname "$0")/.." || exit 1

# Non-blocking startup dependency check: logs missing binaries/ROM-disk
# assets/systemd units to ~/lisa-mini-pi-dependency-check.log every time
# the kiosk starts, so a setup problem on a new/reprovisioned Pi shows up
# there first instead of as a mysterious runtime failure later. See
# check_deps.py's own docstring for what it checks.
python3 check_deps.py >/dev/null 2>&1 &

# Persistent GPIO power-button watcher: runs for the whole X session, not
# just while LisaEm is running - see lisa-power-button-watcher.sh for what
# it actually does on each button press. Logs to its own file since it
# runs detached from any terminal.
./lisa-power-button-watcher.sh >> "$HOME/lisa-power-button-watcher.log" 2>&1 &

export SDL_VIDEODRIVER=x11
exec python3 launcher.py
