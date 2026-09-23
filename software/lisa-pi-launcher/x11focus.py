"""Explicit X11 input-focus/pointer-grab handling, via ctypes bindings to
libX11.

reclaim_focus() exists because pygame.event.set_grab() alone was not
enough to bring keyboard input back after returning from BasiliskII: with
no window manager in this kiosk session, X's own focus-revert behavior
sometimes leaves input focus on no window at all (RevertToNone) once the
emulator's window is destroyed, and SDL's grab does not override that -
so no KEYDOWN events reach this process at all until focus is explicitly
reassigned back to our own window.

release_pointer_grab() targets a related but distinct symptom: it turned
out not to be the actual fix for LisaEm's frozen mouse (see
release_focus_to_pointer_root() below), but is harmless to keep - an
explicit XUngrabPointer still closes a real gap between SDL's grab
bookkeeping and the X server's actual grab state before a new window
maps.

release_focus_to_pointer_root() is what actually explains "LisaEm's
mouse only breaks when launched by clicking, not by pressing Enter":
this kiosk has no window manager riding herd on focus for anything it
didn't itself initiate, and after a mouse click, real input focus can
stay pinned on this (now black, backgrounded) launcher window instead of
transferring to the emulator's newly-mapped one - X pointer motion
routing is stacking-based and mostly focus-independent, but wxWidgets
(LisaEm's toolkit) was observed to just not process mouse-move handling
for a top-level window that the X server doesn't consider focused.
Enter never has this problem because there's no click for anything to
mis-attribute focus around in the first place. Setting focus to
PointerRoot - a special X input-focus mode meaning "whatever window the
pointer physically ends up over, dynamically, needs no window ID known
in advance" - lets the soon-to-map emulator window pick up real focus
itself the moment it appears, the same way it would if no other window
had opinions about focus at all.
"""

import ctypes

import pygame

_REVERT_TO_PARENT = 2
_REVERT_TO_POINTER_ROOT = 1
_POINTER_ROOT = 1
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


def release_focus_to_pointer_root() -> None:
    libx11, display = _open_display()
    if libx11 is None:
        return
    try:
        libx11.XSetInputFocus(
            ctypes.c_void_p(display),
            ctypes.c_ulong(_POINTER_ROOT),
            ctypes.c_int(_REVERT_TO_POINTER_ROOT),
            ctypes.c_ulong(_CURRENT_TIME),
        )
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
