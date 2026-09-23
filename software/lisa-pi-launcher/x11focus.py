"""Explicit X11 input-focus/pointer-grab handling, via ctypes bindings to
libX11.

reclaim_focus() exists because pygame.event.set_grab() alone was not
enough to bring keyboard input back after returning from BasiliskII: with
no window manager in this kiosk session, X's own focus-revert behavior
sometimes leaves input focus on no window at all (RevertToNone) once the
emulator's window is destroyed, and SDL's grab does not override that -
so no KEYDOWN events reach this process at all until focus is explicitly
reassigned back to our own window.

release_pointer_grab() is the same class of bug for the pointer instead
of the keyboard: pygame.event.set_grab(False) releases SDL's own idea of
the grab, but launching LisaEm via a mouse click (not Enter) was
observed to leave the launcher's cursor stuck on screen and LisaEm's own
emulated pointer frozen at its origin - LisaEm's window was never
actually receiving pointer events. An explicit XUngrabPointer closes the
gap between SDL's grab bookkeeping and the X server's actual grab state
before the new window ever maps.
"""

import ctypes

import pygame

_REVERT_TO_PARENT = 2
_CURRENT_TIME = 0


def _open_display():
    try:
        libx11 = ctypes.CDLL("libX11.so.6")
    except OSError:
        return None, None
    libx11.XOpenDisplay.restype = ctypes.c_void_p
    display = libx11.XOpenDisplay(None)
    if not display:
        return None, None
    return libx11, display


def release_pointer_grab() -> None:
    libx11, display = _open_display()
    if libx11 is None:
        return
    try:
        libx11.XUngrabPointer(ctypes.c_void_p(display), ctypes.c_ulong(_CURRENT_TIME))
        libx11.XFlush(ctypes.c_void_p(display))
    finally:
        libx11.XCloseDisplay(ctypes.c_void_p(display))


def reclaim_focus(real_screen: pygame.Surface) -> None:
    wm_info = pygame.display.get_wm_info()
    window_id = wm_info.get("window")
    if not window_id:
        return

    libx11, display = _open_display()
    if libx11 is None:
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
