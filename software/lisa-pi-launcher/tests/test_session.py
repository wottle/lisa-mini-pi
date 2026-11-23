"""Where "Quit" sends you: the desktop if there is one, else a text console."""

import subprocess
from pathlib import Path

import session

SYSTEM_DIR = Path(__file__).resolve().parent.parent / "system"


class FakeRun:
    """Stands in for subprocess.run and records every command."""

    def __init__(self, failing=()):
        self.calls = []
        self.failing = set(failing)

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        code = 1 if tuple(cmd) in self.failing else 0
        return subprocess.CompletedProcess(cmd, code)


def test_a_desktop_is_detected_when_the_lightdm_unit_exists():
    # Catches: treating every machine as if it had a desktop, which made
    # Quit just restart the launcher on Raspberry Pi OS Lite.
    run = FakeRun()
    assert session.desktop_installed(run) is True
    assert run.calls == [["systemctl", "cat", "lightdm.service"]]


def test_no_desktop_is_detected_when_the_lightdm_unit_is_missing():
    # Catches: a missing unit being mistaken for an installed one.
    run = FakeRun(failing=[("systemctl", "cat", "lightdm.service")])
    assert session.desktop_installed(run) is False


def test_no_desktop_is_assumed_when_systemctl_cannot_run():
    # Catches: an exception from a missing systemctl escaping into the launcher loop.
    def broken(cmd, **kwargs):
        raise FileNotFoundError("systemctl")

    assert session.desktop_installed(broken) is False


def test_quit_with_a_desktop_stops_the_watchdog_then_starts_lightdm():
    # Catches: the watchdog restarting the kiosk under the desktop, or the
    # desktop never being started.
    run = FakeRun()
    session.quit_to_session(run)
    assert run.calls == [
        ["systemctl", "cat", "lightdm.service"],
        ["systemctl", "stop", "launcher-watchdog.timer"],
        ["systemctl", "start", "lightdm.service"],
    ]


def test_quit_without_a_desktop_stops_the_watchdog_then_starts_a_console_login():
    # Catches: Quit doing nothing useful on Lite (the launcher exiting and
    # being restarted), or the watchdog bringing the kiosk back from the console.
    run = FakeRun(failing=[("systemctl", "cat", "lightdm.service")])
    session.quit_to_session(run)
    assert run.calls == [
        ["systemctl", "cat", "lightdm.service"],
        ["systemctl", "stop", "launcher-watchdog.timer"],
        ["systemctl", "start", "getty@tty1.service"],
    ]


def test_the_console_login_is_not_started_when_a_desktop_is_available():
    # Catches: starting both sessions on a machine with a desktop.
    run = FakeRun()
    session.quit_to_session(run)
    assert ["systemctl", "start", "getty@tty1.service"] not in run.calls


def test_the_polkit_rule_lets_the_kiosk_user_start_the_console_login():
    # Catches: Quit on Lite being refused by polkit, because the rule only
    # listed the launcher, the watchdog and lightdm.
    text = (SYSTEM_DIR / "10-lisa-launcher-power.rules").read_text()
    assert '"getty@tty1.service"' in text


def test_the_launcher_unit_gives_up_the_screen_to_the_console_login():
    # Catches: someone removing Conflicts=getty@tty1, which is what makes
    # starting the console login stop the kiosk.
    text = (SYSTEM_DIR / "launcher.service").read_text()
    assert "getty@tty1.service" in text.split("Conflicts=", 1)[1].splitlines()[0]
