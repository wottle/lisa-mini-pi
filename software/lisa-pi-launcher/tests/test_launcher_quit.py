"""Quit wired into the real launcher loop (see test_launcher_autostart.py
for how these drive launcher.main() under the dummy video driver)."""

import sys

import pygame

import session
from tests.test_launcher_autostart import (  # noqa: F401 (env is a fixture)
    Env,
    env,
    launcher_is_up,
    press,
    press_until,
    wait_until,
)


def confirm_quit():
    launcher_is_up()
    press(pygame.K_q)
    pygame.time.wait(300)
    press(pygame.K_RETURN)


def test_quit_without_a_desktop_opens_the_terminal_and_the_picker_returns(env, monkeypatch, tmp_path):
    # Catches: Quit doing nothing useful on Lite (the launcher just
    # restarting), the terminal not opening, or the picker not coming back
    # when the terminal is closed.
    log = tmp_path / "terminal.log"
    monkeypatch.setattr(session, "desktop_installed", lambda *a, **k: False)
    monkeypatch.setattr(session, "terminal_command",
                        lambda: [sys.executable, "-c", f"open({str(log)!r}, 'a').write('opened\\n')"])
    seen = []

    def script():
        confirm_quit()
        seen.append(wait_until(lambda: log.exists() and log.read_text().split() == ["opened"]))
        # the picker is alive again: A marks the highlighted system
        env.store.get()
        seen.append(press_until(pygame.K_a, lambda: env.store.get() == "sys1"))

    env.run(script)
    assert seen == [True, True]


def test_quit_with_a_desktop_hands_over_to_it_and_ends_the_launcher(env, monkeypatch, tmp_path):
    # Catches: the desktop path being lost, or the terminal opening as well.
    handed_over = []
    log = tmp_path / "terminal.log"
    monkeypatch.setattr(session, "desktop_installed", lambda *a, **k: True)
    monkeypatch.setattr(session, "quit_to_desktop", lambda *a, **k: handed_over.append(True))
    monkeypatch.setattr(session, "terminal_command",
                        lambda: [sys.executable, "-c", f"open({str(log)!r}, 'a').write('opened\\n')"])

    env.run(confirm_quit)

    assert handed_over == [True]
    assert not log.exists()
