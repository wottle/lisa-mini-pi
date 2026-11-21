"""Entry point: fullscreen pygame kiosk showing a keyboard/mouse-driven
"CHOOSE YOUR ADVENTURE" system picker, launching the selected emulator as
a subprocess and returning to the picker when it exits."""

import os
import subprocess
import sys
import time

# Must be set before pygame.init() creates the display. SDL auto-minimizes
# an exclusive-fullscreen window when it loses input focus by default. That
# hint was never observed under the old no-window-manager kiosk session
# (focus loss was never reliably detected there), but now that openbox
# correctly hands focus to a newly-launched emulator's window, this
# launcher's own window legitimately loses focus - and without this,
# SDL would iconify/unmap it, leaving nothing on screen to return to once
# the emulator exits.
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")

# SDL2 auto-captures the mouse on a button press by default (so a
# click-drag that leaves the window still tracks correctly), releasing
# that capture only once SDL itself processes the matching button-release
# event. Selecting a system with a mouse click goes straight from that
# MOUSEBUTTONDOWN into a blocking subprocess.run() for the whole emulator
# session - SDL never gets to pump the button-release, so its capture
# grab was suspected of outliving the click and silently swallowing all
# pointer events meant for the emulator's window (window-manager focus
# and an X pointer grab are independent - LisaEm correctly had real focus
# the whole time per an xdotool diagnostic, yet still never received a
# single mouse event). Disabling auto-capture removes that grab from the
# picture entirely rather than trying to race its release.
os.environ.setdefault("SDL_MOUSE_AUTO_CAPTURE", "0")

import pygame

_DIAG_EVENT_NAMES = {
    pygame.ACTIVEEVENT: "ACTIVEEVENT",
    pygame.WINDOWFOCUSGAINED: "WINDOWFOCUSGAINED",
    pygame.WINDOWFOCUSLOST: "WINDOWFOCUSLOST",
    pygame.WINDOWTAKEFOCUS: "WINDOWTAKEFOCUS",
    pygame.WINDOWSHOWN: "WINDOWSHOWN",
    pygame.KEYDOWN: "KEYDOWN",
}


_DIAG_LOG_PATH = "/home/wottle/lisa-pi-launcher/focus_diag.log"


def _diag_log(msg: str) -> None:
    line = f"[FOCUS-DIAG {time.time():.3f}] {msg}"
    print(line, flush=True)
    try:
        with open(_DIAG_LOG_PATH, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass

import cursor
import theme
import x11focus
from bitmap_font import CHAR_WIDTH  # noqa: F401 (documents the font dependency)
from config import load_config
from rendering import (
    ItemVisual,
    confirmation_hit_test,
    draw_checkerboard_cached,
    draw_confirmation_dialog,
    footer_hit_test,
    hit_test,
    render_frame,
)
from redraw import RedrawGate
from state import LauncherState, Phase

# The Lisa-style boot-diagnostic animation (CPU/MEM/I/O/EXPANSION test,
# see boot_diag.py) is disabled as of the 2026-09-25 "CHOOSE YOUR
# ADVENTURE" redesign - the picker now shows immediately on launch, no
# animated pre-phase. boot_diag.py itself is left in place (and its own
# tests still pass) in case it's ever wanted back; this file simply
# doesn't import or call it anymore.


# Window events after which the screen contents may be stale and must be
# repainted even though nothing in the launcher's own state changed.
_REPAINT_EVENTS = tuple(
    getattr(pygame, name) for name in (
        "VIDEOEXPOSE", "WINDOWEXPOSED", "WINDOWSHOWN", "WINDOWRESTORED",
        "WINDOWMAXIMIZED", "WINDOWFOCUSGAINED", "WINDOWENTER",
    ) if hasattr(pygame, name)
)


def _load_icon(path: str) -> pygame.Surface:
    icon = pygame.image.load(path).convert()
    # The icon PNGs are 128px. On a larger panel theme.apply_scale() has
    # already grown ICON_SIZE by a whole multiple, so enlarge to match with
    # nearest-neighbour (crisp pixel art, no blur). Must run after apply_scale().
    if icon.get_size() != (theme.ICON_SIZE, theme.ICON_SIZE):
        icon = pygame.transform.scale(icon, (theme.ICON_SIZE, theme.ICON_SIZE))
    return icon


def _system_items_visual(state: LauncherState, icons: dict[str, pygame.Surface]) -> list[ItemVisual]:
    items = []
    for index, system in enumerate(state.systems):
        items.append(ItemVisual(
            icon=icons[system.id],
            label=system.name,
            status_icon=None,
            selected=(index == state.selected_index),
            subtitle=system.subtitle,
        ))
    return items


def _draw_frame(
    real_screen: pygame.Surface,
    header_text: str,
    items: list[ItemVisual],
    hovered_footer: str | None = None,
) -> None:
    # The checkerboard is drawn directly onto real_screen at its own
    # native resolution (never scaled, so it never aliases/moires);
    # render_frame then draws the opaque panel directly on top of it, on
    # this same surface - see theme.py for why there's no separate
    # logical surface scaled up to this one anymore.
    draw_checkerboard_cached(real_screen, theme.CHECKER_CELL_SIZE)
    render_frame(real_screen, header_text, items, hovered_footer=hovered_footer)
    pygame.display.flip()


def _draw_confirmation(
    real_screen: pygame.Surface,
    header_text: str,
    items: list[ItemVisual],
    action: str,
    hovered: str | None,
) -> None:
    # The picker stays visible underneath the dialog (matches how a modal
    # dialog normally sits over its parent window) rather than blanking
    # the screen.
    draw_checkerboard_cached(real_screen, theme.CHECKER_CELL_SIZE)
    render_frame(real_screen, header_text, items)
    draw_confirmation_dialog(real_screen, action, hovered=hovered)
    pygame.display.flip()


def _open_fullscreen() -> pygame.Surface:
    # (0, 0) tells SDL to use the current desktop resolution for fullscreen,
    # so the launcher fills whatever display it's actually running on.
    # The picker's layout is the 1024x768 design scaled by a whole number
    # and centred - main() calls theme.apply_scale() with the surface size.
    return pygame.display.set_mode((0, 0), pygame.FULLSCREEN)


def main() -> None:
    pygame.init()
    pygame.mouse.set_visible(True)
    cursor.set_cursor()
    # With no window manager to broker input focus, X11's default focus
    # revert-to behavior after the emulator's window closes doesn't
    # reliably bring keyboard focus back to this window (mouse events
    # still worked, since those aren't focus-gated) - grabbing input
    # explicitly forces it back here regardless of what X would have done
    # on its own.
    pygame.event.set_grab(True)

    real_screen = _open_fullscreen()
    theme.apply_scale(*real_screen.get_size())
    clock = pygame.time.Clock()

    systems = load_config("config.json")

    icons: dict[str, pygame.Surface] = {}
    for system in systems:
        icons[system.id] = _load_icon(system.icon)

    state = LauncherState(systems)

    def _perform_confirmed_action(action: str) -> bool:
        """Runs whatever S/Q used to do immediately - now only reached
        after the user has confirmed the dialog. Returns False if the
        main loop should stop running (the Q/quit-to-desktop case)."""
        if action == "shutdown":
            subprocess.run(["systemctl", "poweroff"])
            return True
        # action == "quit": suppress the watchdog first - it doesn't know
        # about the desktop session and would otherwise see no
        # launcher/emulator process running and restart the kiosk out
        # from under it within 30s. Starting lightdm.service is what
        # actually switches sessions (see launcher.service's
        # Conflicts=lightdm.service - starting it auto-stops us, which is
        # why this is the last action taken here).
        subprocess.run(["systemctl", "stop", "launcher-watchdog.timer"])
        subprocess.run(["systemctl", "start", "lightdm.service"])
        return False

    running = True
    hovered_footer: str | None = None
    hovered_confirm: str | None = None
    # Only repaint when something visible changed (see redraw.py) - drawing
    # the full frame 30x/s while idle kept a core near 50% busy.
    gate = RedrawGate(refresh_seconds=1.0)
    while running:
        clock.tick(30)

        for event in pygame.event.get():
            if event.type in _REPAINT_EVENTS:
                gate.invalidate()
            if event.type in _DIAG_EVENT_NAMES:
                grab_state = pygame.event.get_grab()
                active_state = pygame.display.get_active()
                _diag_log(f"{_DIAG_EVENT_NAMES[event.type]} grab={grab_state} active={active_state} raw={event}")

            if event.type == pygame.QUIT:
                running = False
            elif state.phase == Phase.CONFIRMING:
                # SHUT DOWN/QUIT are destructive/disruptive enough to need
                # an explicit confirmation step - see the
                # 2026-09-27 clickable-footer decision. While confirming,
                # only RETURN/ESCAPE and the dialog's own CONFIRM/CANCEL
                # buttons do anything; arrow keys, item clicks, etc. are
                # ignored so a stray keypress can't launch a system or
                # move the selection underneath the dialog.
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        action = state.confirm_pending()
                        hovered_confirm = None
                        if not _perform_confirmed_action(action):
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        state.cancel_pending()
                        hovered_confirm = None
                elif event.type == pygame.MOUSEMOTION:
                    hovered_confirm = confirmation_hit_test(event.pos)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    choice = confirmation_hit_test(event.pos)
                    if choice == "confirm":
                        action = state.confirm_pending()
                        hovered_confirm = None
                        if not _perform_confirmed_action(action):
                            running = False
                    elif choice == "cancel":
                        state.cancel_pending()
                        hovered_confirm = None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    state.move_selection(-1)
                elif event.key == pygame.K_RIGHT:
                    state.move_selection(1)
                elif event.key == pygame.K_RETURN:
                    real_screen = _launch_selected(state, real_screen, icons)
                    gate.invalidate()
                elif event.key == pygame.K_s:
                    state.request_confirmation("shutdown")
                    hovered_footer = None
                elif event.key == pygame.K_r:
                    # Not shown in the footer hint (only S/Q are), and
                    # deliberately left out of the confirmation-dialog
                    # treatment added for S/Q - see the 2026-09-27
                    # decision to leave R exactly as it was.
                    subprocess.run(["systemctl", "reboot"])
                elif event.key == pygame.K_q:
                    state.request_confirmation("quit")
                    hovered_footer = None
            elif event.type == pygame.MOUSEMOTION:
                # Hover selects, mirroring the arrow keys - so someone
                # without a keyboard can see what they're about to pick
                # before committing with a click. event.pos is already in
                # screen coordinates, matching item_layout()/hit_test()
                # directly now that there's no separate logical surface.
                index = hit_test(_system_items_visual(state, icons), event.pos)
                if index is not None:
                    state.select_index(index)
                hovered_footer = footer_hit_test(_system_items_visual(state, icons), event.pos)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                footer_choice = footer_hit_test(_system_items_visual(state, icons), event.pos)
                if footer_choice is not None:
                    state.request_confirmation(footer_choice)
                    hovered_footer = None
                else:
                    index = hit_test(_system_items_visual(state, icons), event.pos)
                    if index is not None:
                        state.select_index(index)
                        real_screen = _launch_selected(state, real_screen, icons)
                        gate.invalidate()

        view_key = (
            state.phase, state.selected_index, state.header_text(),
            state.pending_action, hovered_footer, hovered_confirm,
        )
        if gate.should_draw(view_key):
            items = _system_items_visual(state, icons)
            if state.phase == Phase.CONFIRMING:
                _draw_confirmation(real_screen, state.header_text(), items, state.pending_action, hovered_confirm)
            else:
                _draw_frame(real_screen, state.header_text(), items, hovered_footer)

    pygame.quit()


def _launch_selected(
    state: LauncherState,
    real_screen: pygame.Surface,
    icons: dict[str, pygame.Surface],
) -> pygame.Surface:
    state.start_selected()

    # Render and flip one STARTING-phase frame first, so the
    # "STARTING <NAME>..." header text is actually visible for a moment
    # rather than being set and discarded before the next flip.
    items = _system_items_visual(state, icons)
    _draw_frame(real_screen, state.header_text(), items)

    # Cover the screen in solid black and leave this window mapped, rather
    # than tearing the display down and recreating it. There's no window
    # manager in this kiosk session to iconify/hide us any other way, and
    # destroying and recreating the display briefly exposes the bare X11
    # root window (the desktop background) in the gap. Left mapped and
    # black, this window just sits behind whatever the emulator maps on
    # top of it - X11 stacks a newly-mapped window above existing ones by
    # default with no window manager involved - and reappears exactly as
    # it was the instant the emulator's window is gone.
    real_screen.fill((0, 0, 0))
    pygame.display.flip()

    # Release input grab so the emulator's own window can actually receive
    # keyboard/mouse input - holding it while a second window is meant to
    # be focused would fight the emulator for input.
    pygame.event.set_grab(False)
    # pygame.event.set_grab(False) alone releases SDL's own bookkeeping
    # but was observed to leave the actual X11 pointer grab in place when
    # launching via a mouse click (not Enter) - see x11focus.py's
    # release_pointer_grab() docstring for the symptom this fixes.
    x11focus.release_pointer_grab()
    # The actual fix for LisaEm's mouse freezing when launched by click:
    # let the emulator's about-to-map window pick up real X input focus
    # itself instead of leaving it pinned on this (now backgrounded)
    # window - see release_focus_to_pointer_root()'s docstring.
    x11focus.release_focus_to_pointer_root()
    # Basilisk II and Mini vMac both take over the cursor themselves once
    # running, so the launcher's big custom pointer naturally disappears;
    # LisaEm never touches cursor state at all, so without this it just
    # keeps showing our last-defined cursor image on top of LisaEm's own
    # screen for the whole session. Hide it explicitly instead of
    # depending on each emulator's own behavior.
    pygame.mouse.set_visible(False)
    _diag_log(f"pre-launch grab={pygame.event.get_grab()} active={pygame.display.get_active()}")

    launch_failed = False
    try:
        # start_new_session detaches the emulator into its own process
        # group. Without it, the emulator shares this process's group by
        # default, and at least one emulator (Basilisk II) sends a signal
        # to its whole process group as part of its shutdown sequence -
        # which was killing this launcher process too, silently, with no
        # traceback, the instant the guest OS finished shutting down.
        subprocess.run(state.selected.command, start_new_session=True)
    except OSError:
        # Missing binary, permission denied, etc. Don't let a bad
        # `command` entry crash the whole kiosk process - under
        # Restart=always that would just silently respawn back to the
        # picker with no indication of what went wrong.
        launch_failed = True
    finally:
        state.finish_starting()
        _diag_log(f"post-subprocess.run() returned, launch_failed={launch_failed} "
                  f"grab-before-reclaim={pygame.event.get_grab()} active={pygame.display.get_active()}")
        # Reclaim input focus now that the emulator's window is gone (see
        # the comment in main() - X11 doesn't reliably hand it back on
        # its own with no window manager in this session).
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(True)
        x11focus.reclaim_focus(real_screen)
        _diag_log(f"grab-after-reclaim={pygame.event.get_grab()} active={pygame.display.get_active()}")
        # Drain keystrokes queued while the emulator subprocess was
        # running, so e.g. a leftover Enter doesn't immediately relaunch
        # it once the picker's event loop resumes.
        pygame.event.clear()

    if launch_failed:
        _draw_frame(real_screen, "LAUNCH FAILED", _system_items_visual(state, icons))
        pygame.time.wait(1000)

    return real_screen


if __name__ == "__main__":
    sys.exit(main() or 0)
