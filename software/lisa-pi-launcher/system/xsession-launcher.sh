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

# Persistent GPIO power-button watcher: runs for the whole X session,
# independent of whether the launcher menu or an emulator is currently
# showing (see lisa-power-button-watcher.sh for the on/off logic).
/home/wottle/lisa-power-button-watcher.sh >> /home/wottle/lisa-run-with-led.log 2>&1 &

cd /home/wottle/lisa-pi-launcher || exit 1
export SDL_VIDEODRIVER=x11
exec python3 launcher.py
