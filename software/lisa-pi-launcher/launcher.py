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
from rendering import ItemVisual, draw_checkerboard_cached, hit_test, hit_test_footer, render_frame
from state import LauncherState, Phase

# The Lisa-style boot-diagnostic animation (CPU/MEM/I/O/EXPANSION test,
# see boot_diag.py) is disabled as of the 2026-09-25 "CHOOSE YOUR
# ADVENTURE" redesign - the picker now shows immediately on launch, no
# animated pre-phase. boot_diag.py itself is left in place (and its own
# tests still pass) in case it's ever wanted back; this file simply
# doesn't import or call it anymore.


def _load_icon(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert()


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
) -> None:
    # The checkerboard is drawn directly onto real_screen at its own
    # native resolution (never scaled, so it never aliases/moires);
    # render_frame then draws the opaque panel directly on top of it, on
    # this same surface - see theme.py for why there's no separate
    # logical surface scaled up to this one anymore.
    draw_checkerboard_cached(real_screen, theme.CHECKER_CELL_SIZE)
    render_frame(real_screen, header_text, items)
    pygame.display.flip()


def _quit_to_desktop() -> None:
    # Suppress the watchdog first - it doesn't know about the desktop
    # session and would otherwise see no launcher/emulator process
    # running and restart the kiosk out from under it within 30s.
    # Starting lightdm.service is what actually switches sessions (see
    # launcher.service's Conflicts=lightdm.service - starting it
    # auto-stops us, which is why this is the last action taken here).
    subprocess.run(["systemctl", "stop", "launcher-watchdog.timer"])
    subprocess.run(["systemctl", "start", "lightdm.service"])


def _open_fullscreen() -> pygame.Surface:
    # (0, 0) tells SDL to use the current desktop resolution for fullscreen,
    # so the launcher fills whatever display it's actually running on
    # instead of a fixed 1024x768 that may not match the real panel. The
    # picker's own content is still laid out for a fixed 1024x768 (see
    # theme.py) - on a differently-sized display it draws at that fixed
    # size/position rather than adapting, which is an accepted tradeoff.
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
    clock = pygame.time.Clock()

    systems = load_config("config.json")

    icons: dict[str, pygame.Surface] = {}
    for system in systems:
        icons[system.id] = _load_icon(system.icon)

    state = LauncherState(systems)

    running = True
    while running:
        clock.tick(30)

        for event in pygame.event.get():
            if event.type in _DIAG_EVENT_NAMES:
                grab_state = pygame.event.get_grab()
                active_state = pygame.display.get_active()
                _diag_log(f"{_DIAG_EVENT_NAMES[event.type]} grab={grab_state} active={active_state} raw={event}")

            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if state.phase == Phase.CONFIRM_SHUTDOWN:
                    # Y/S/RETURN confirm (S so re-pressing the same key
                    # that opened the prompt also confirms it); any other
                    # key backs out without powering off.
                    if event.key in (pygame.K_y, pygame.K_s, pygame.K_RETURN):
                        subprocess.run(["systemctl", "poweroff"])
                    else:
                        state.cancel()
                elif event.key == pygame.K_LEFT:
                    state.move_selection(-1)
                elif event.key == pygame.K_RIGHT:
                    state.move_selection(1)
                elif event.key == pygame.K_RETURN:
                    real_screen = _launch_selected(state, real_screen, icons)
                elif event.key == pygame.K_s:
                    state.request_shutdown()
                elif event.key == pygame.K_r:
                    # Not shown in the footer hint (only S/Q are), but
                    # still works - see the 2026-09-25 redesign decision.
                    subprocess.run(["systemctl", "reboot"])
                elif event.key == pygame.K_q:
                    _quit_to_desktop()
                    running = False
            elif event.type == pygame.MOUSEMOTION:
                # Hover selects, mirroring the arrow keys - so someone
                # without a keyboard can see what they're about to pick
                # before committing with a click. event.pos is already in
                # screen coordinates, matching item_layout()/hit_test()
                # directly now that there's no separate logical surface.
                # Suppressed during the shutdown confirmation prompt so
                # hovering over the (still-visible) item grid can't change
                # the selection out from under the prompt.
                if state.phase != Phase.CONFIRM_SHUTDOWN:
                    index = hit_test(_system_items_visual(state, icons), event.pos)
                    if index is not None:
                        state.select_index(index)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if state.phase == Phase.CONFIRM_SHUTDOWN:
                    # Mirrors the keyboard: clicking the same "S SHUT
                    # DOWN" footer text that opened the prompt confirms
                    # it; clicking anywhere else cancels - this is what
                    # lets a mouse-only setup both trigger and confirm a
                    # shutdown with no keyboard at all.
                    if hit_test_footer(_system_items_visual(state, icons), event.pos) == "shutdown":
                        subprocess.run(["systemctl", "poweroff"])
                    else:
                        state.cancel()
                    continue
                footer_action = hit_test_footer(_system_items_visual(state, icons), event.pos)
                if footer_action == "shutdown":
                    state.request_shutdown()
                elif footer_action == "quit":
                    _quit_to_desktop()
                    running = False
                else:
                    index = hit_test(_system_items_visual(state, icons), event.pos)
                    if index is not None:
                        state.select_index(index)
                        real_screen = _launch_selected(state, real_screen, icons)

        items = _system_items_visual(state, icons)
        _draw_frame(real_screen, state.header_text(), items)

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
