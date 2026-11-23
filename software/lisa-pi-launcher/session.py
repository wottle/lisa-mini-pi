"""Where "Quit" sends you.

On Raspberry Pi OS with the desktop, Quit starts the desktop (lightdm). On
Raspberry Pi OS Lite there is no desktop, so Quit starts a text console
login on the panel instead. Either way the kiosk steps aside because
launcher.service declares Conflicts= with both lightdm.service and
getty@tty1.service: starting one of them stops the launcher.
"""

import subprocess

DESKTOP_UNIT = "lightdm.service"
CONSOLE_UNIT = "getty@tty1.service"
WATCHDOG_TIMER = "launcher-watchdog.timer"


def desktop_installed(run=subprocess.run) -> bool:
    """True if the desktop's display manager unit exists on this machine."""
    try:
        result = run(["systemctl", "cat", DESKTOP_UNIT],
                     capture_output=True, text=True)
    except OSError:
        return False
    return result.returncode == 0


def quit_to_session(run=subprocess.run) -> None:
    """Hand the screen over. The last command stops the launcher itself (via
    Conflicts=), so nothing may be run after it."""
    target = DESKTOP_UNIT if desktop_installed(run) else CONSOLE_UNIT
    # The watchdog does not know about the other session; left running it
    # would see no launcher or emulator and restart the kiosk within 30 s.
    run(["systemctl", "stop", WATCHDOG_TIMER])
    run(["systemctl", "start", target])
