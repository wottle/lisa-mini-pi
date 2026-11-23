"""Where "Quit" sends you: the desktop if there is one, else a terminal."""

import subprocess

import session


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


def test_quitting_to_the_desktop_stops_the_watchdog_then_starts_lightdm():
    # Catches: the watchdog restarting the kiosk under the desktop, or the
    # desktop never being started. Starting lightdm stops the launcher, so
    # it must be the last command.
    run = FakeRun()
    session.quit_to_desktop(run)
    assert run.calls == [
        ["systemctl", "stop", "launcher-watchdog.timer"],
        ["systemctl", "start", "lightdm.service"],
    ]


def test_the_terminal_is_a_full_screen_xterm_that_says_how_to_get_back():
    # Catches: a terminal that opens as a small window in the kiosk, or one
    # that gives no clue how to return to the picker.
    cmd = session.terminal_command()
    assert cmd[0] == "xterm"
    assert "-fullscreen" in cmd
    assert "exit" in cmd[-1]
