"""Explicit X11 input-focus reclaim, via ctypes bindings to libX11.

Needed because pygame.event.set_grab() alone was not enough to bring
keyboard input back after returning from BasiliskII: with no window
manager in this kiosk session, X's own focus-revert behavior sometimes
leaves input focus on no window at all (RevertToNone) once the emulator's
window is destroyed, and SDL's grab does not override that - so no
KEYDOWN events reach this process at all until focus is explicitly
reassigned back to our own window.
"""

import ctypes

import pygame

_REVERT_TO_PARENT = 2
_CURRENT_TIME = 0


def reclaim_focus(real_screen: pygame.Surface) -> None:
    wm_info = pygame.display.get_wm_info()
    window_id = wm_info.get("window")
    if not window_id:
        return

    try:
        libx11 = ctypes.CDLL("libX11.so.6")
    except OSError:
        return

    libx11.XOpenDisplay.restype = ctypes.c_void_p
    display = libx11.XOpenDisplay(None)
    if not display:
        return

    try:
        libx11.XSetInputFocus(
            ctypes.c_void_p(display),
            ctypes.c_ulong(window_id),
            ctypes.c_int(_REVERT_TO_PARENT),
            ctypes.c_ulong(_CURRENT_TIME),
        )
        libx11.XFlush(ctypes.c_void_p(display))
    finally:
        libx11.XCloseDisplay(ctypes.c_void_p(display))
