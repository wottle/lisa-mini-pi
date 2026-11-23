"""Where "Quit" sends you.

On Raspberry Pi OS with the desktop, Quit starts the desktop (lightdm); that
stops the kiosk, because launcher.service declares Conflicts=lightdm.service.

Raspberry Pi OS Lite has no desktop. There Quit opens a full-screen terminal
inside the kiosk's own X session, the same way an emulator is launched, and
the picker returns when the terminal is closed. (Dropping to a text console
on the real screen was tried first: on the Pi 4 the display stayed black
after X exited, the same vc4 hand-off problem system/back-to-kiosk.sh
describes.)
"""

import subprocess

DESKTOP_UNIT = "lightdm.service"
WATCHDOG_TIMER = "launcher-watchdog.timer"


def desktop_installed(run=subprocess.run) -> bool:
    """True if the desktop's display manager unit exists on this machine."""
    try:
        result = run(["systemctl", "cat", DESKTOP_UNIT],
                     capture_output=True, text=True)
    except OSError:
        return False
    return result.returncode == 0


def quit_to_desktop(run=subprocess.run) -> None:
    """Hand the screen to the desktop. Starting lightdm stops the launcher
    itself (via Conflicts=), so it must be the last thing done."""
    # The watchdog does not know about the desktop session; left running it
    # would see no launcher or emulator and restart the kiosk within 30 s.
    run(["systemctl", "stop", WATCHDOG_TIMER])
    run(["systemctl", "start", DESKTOP_UNIT])


def terminal_command() -> list[str]:
    """A full-screen terminal that tells you how to get back."""
    hint = 'echo "Type exit to return to the launcher."; echo; exec "${SHELL:-/bin/bash}"'
    return ["xterm", "-fullscreen", "-title", "Terminal",
            "-fa", "Monospace", "-fs", "16", "-bg", "black", "-fg", "white",
            "-e", "sh", "-c", hint]
