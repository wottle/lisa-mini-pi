"""The auto-start feature wired into the real launcher loop.

These run launcher.main() itself under pygame's dummy video driver. The
"emulators" are real child processes that append their system id to a log
file, so what happened is observed from the outside. Keys are posted from a
helper thread, the way a person would press them.
"""

import json
import os
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

import cursor
import launcher
import theme
from autostart import AutoStart
from redraw import RedrawGate
from rendering import ItemVisual, auto_tag_rect, item_layout

ICON = os.path.join(os.path.dirname(launcher.__file__), "icons", "lisa.png")
IDS = ["sys1", "sys2", "sys3"]


def wait_until(condition, timeout=6.0):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(0.02)
    return False


def press(key):
    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode="", scancode=0))


def launcher_is_up():
    """True once main() has opened its display and is looping."""
    wait_until(lambda: pygame.display.get_init() and pygame.display.get_surface() is not None)
    time.sleep(0.3)


def press_until(key, condition, timeout=6.0):
    """Press `key` until `condition` holds. A press made while the launcher is
    still busy (for example right after an emulator exits, when it drains
    queued keys on purpose) is simply lost, so try again."""
    end = time.time() + timeout
    while time.time() < end:
        press(key)
        if wait_until(condition, timeout=0.5):
            return True
    return False


def quit_launcher():
    try:
        pygame.event.post(pygame.event.Event(pygame.QUIT))
    except pygame.error:  # the launcher has already shut pygame down
        pass


class Env:
    def __init__(self, tmp_path):
        self.log = tmp_path / "launched.log"
        boot = tmp_path / "boot_id"
        boot.write_text("boot-A\n")
        self.store = AutoStart(tmp_path / "cfg", boot_id_path=boot)

    def launched(self):
        return self.log.read_text().split() if self.log.exists() else []

    def run(self, script):
        """Run launcher.main() while `script` presses keys from another thread.
        When the script ends it keeps asking the launcher to quit until main()
        actually returns (the launcher drains queued keys when an emulator exits,
        so a single quit can be lost). A watchdog stops a hung run."""
        finished = threading.Event()

        def driver():
            try:
                script()
            finally:
                while not finished.is_set():
                    quit_launcher()
                    finished.wait(0.2)

        def watchdog():
            if not finished.wait(20):
                quit_launcher()

        threading.Thread(target=driver, daemon=True).start()
        threading.Thread(target=watchdog, daemon=True).start()
        try:
            launcher.main(self.store)
        finally:
            finished.set()


@pytest.fixture
def env(tmp_path, monkeypatch):
    systems = [
        {
            "id": sid, "name": sid.upper(), "subtitle": "TEST", "icon": ICON,
            "command": [sys.executable, "-c",
                        f"open({str(tmp_path / 'launched.log')!r}, 'a').write({sid!r} + '\\n')"],
        }
        for sid in IDS
    ]
    (tmp_path / "config.json").write_text(json.dumps({"systems": systems}))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cursor, "set_cursor", lambda *a, **k: None)  # the dummy video driver has no cursors
    yield Env(tmp_path)
    theme.apply_scale(1024, 768)  # main() rescales the layout to the dummy screen; restore for other tests


def test_A_marks_the_highlighted_system_and_a_second_press_clears_it(env):
    # Catches: the key not being wired, marking the first system instead of
    # the highlighted one, or a second press not clearing the mark.
    seen = []

    def script():
        launcher_is_up()
        press(pygame.K_RIGHT)
        time.sleep(0.2)
        press(pygame.K_a)
        seen.append(wait_until(lambda: env.store.get() == "sys2"))
        press(pygame.K_a)
        seen.append(wait_until(lambda: env.store.get() is None))

    env.run(script)
    assert seen == [True, True]


def test_a_marked_system_launches_at_power_on_and_the_picker_follows_when_it_exits(env):
    # Catches: no auto-launch, the wrong system launching, the picker not
    # returning afterwards, or the highlight not being on what just ran.
    env.store.toggle("sys2")
    seen = []

    def script():
        seen.append(wait_until(lambda: env.launched() == ["sys2"]))
        # the picker is alive and sys2 is the highlighted one: A clears its mark
        seen.append(press_until(pygame.K_a, lambda: env.store.get() is None))

    env.run(script)
    assert seen == [True, True]
    assert env.launched() == ["sys2"]


def test_a_second_start_in_the_same_boot_shows_the_picker_instead(env):
    # Catches: the launcher loop ignoring the once-per-boot rule, which would
    # retry a possibly broken emulator after every restart.
    env.store.toggle("sys1")
    env.run(lambda: wait_until(lambda: env.launched() == ["sys1"]))
    assert env.launched() == ["sys1"]
    env.run(lambda: time.sleep(0.8))  # the launcher restarted in the same boot
    assert env.launched() == ["sys1"]


def test_nothing_launches_by_itself_when_nothing_is_marked(env):
    # Catches: an emulator starting by default on a machine with no setting.
    env.run(lambda: time.sleep(0.8))
    assert env.launched() == []


def test_the_tag_appears_on_screen_right_after_pressing_A(env, monkeypatch):
    # Catches: the screen not repainting after the key (the redraw gate not
    # being told the mark changed). The safety refresh is pushed out to an
    # hour so only a real state change can repaint.
    monkeypatch.setattr(launcher, "RedrawGate", lambda refresh_seconds=1.0: RedrawGate(refresh_seconds=3600))
    seen = []

    def tag_is_drawn():
        screen = pygame.display.get_surface()
        icon = pygame.Surface((theme.ICON_SIZE, theme.ICON_SIZE))
        items = [ItemVisual(icon=icon, label=s, status_icon=None, selected=(i == 0), subtitle="TEST", auto=True)
                 for i, s in enumerate(IDS)]
        tag = auto_tag_rect(item_layout(items)[0])
        # sys1 is highlighted, so its tag is white on the black card
        return screen.get_at((tag.left + 1, tag.top + 1))[:3] == (255, 255, 255)

    def script():
        launcher_is_up()
        press(pygame.K_a)
        seen.append(wait_until(tag_is_drawn, timeout=1.0))

    env.run(script)
    assert seen == [True]
