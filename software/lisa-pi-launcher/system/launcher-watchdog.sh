#!/bin/sh
# Safety net, run periodically by launcher-watchdog.timer: if neither the
# launcher nor any configured emulator is running, something has gone
# wrong in a way launcher.service's own Restart=always didn't catch (e.g.
# the whole X session died without the launcher process itself exiting)
# - restart the kiosk service to recover.
#
# Update this list if config.json gains emulators beyond LisaEm/Basilisk II.
if pgrep -f "python3 launcher\.py$" > /dev/null 2>&1; then
    exit 0
fi
if pgrep -x lisaem > /dev/null 2>&1; then
    exit 0
fi
if pgrep -x BasiliskII > /dev/null 2>&1; then
    exit 0
fi

echo "launcher-watchdog: neither the launcher nor a known emulator is running - restarting launcher.service"
systemctl restart launcher.service
