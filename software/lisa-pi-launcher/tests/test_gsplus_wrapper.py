"""gsplus-run-with-led.sh, run for real with a stand-in for GSplus."""

import os
import stat
import subprocess
import sys
from pathlib import Path

WRAPPER = Path(__file__).resolve().parent.parent / "gsplus-run-with-led.sh"


def fake_gsplus(tmp_path, body):
    binary = tmp_path / "gsplus"
    binary.write_text("#!/bin/sh\n" + body)
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
    return binary


def env_for(tmp_path, binary):
    env = dict(os.environ)
    env.update(HOME=str(tmp_path), GSPLUS_DIR=str(tmp_path), GSPLUS_BIN=str(binary),
               GSPLUS_CFG=str(tmp_path / "config.kegs"))
    return env


def test_gsplus_does_not_inherit_the_launchers_terminal_input(tmp_path):
    # Catches: GSplus blocking on its input after its window is closed. Under
    # launcher.service the child's standard input is a terminal, and GSplus's
    # debugger thread reads it, so it never finished shutting down (the window
    # closed but the process stayed, and the picker never came back). Here
    # the wrapper's input is a pipe that is never closed, which blocks any
    # reader that inherits it.
    out = tmp_path / "result"
    binary = fake_gsplus(tmp_path, f'cat >/dev/null\necho finished > "{out}"\n')
    proc = subprocess.Popen([str(WRAPPER), "-rom", "R", "-s7d1", "D"],
                            stdin=subprocess.PIPE, env=env_for(tmp_path, binary))
    try:
        assert proc.wait(timeout=10) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.stdin.close()
    assert out.read_text().strip() == "finished"


def test_gsplus_is_started_with_the_config_and_the_launchers_arguments(tmp_path):
    # Catches: the ROM and disk from config.json not reaching GSplus, or the
    # seeded config not being used.
    args_file = tmp_path / "args"
    binary = fake_gsplus(tmp_path, f'echo "$@" > "{args_file}"\n')
    subprocess.run([str(WRAPPER), "-rom", "/h/ROM.01", "-s7d1", "/h/gsos.hdv"],
                   stdin=subprocess.DEVNULL, env=env_for(tmp_path, binary), check=True, timeout=10)
    assert args_file.read_text().split() == [
        "-cfg", str(tmp_path / "config.kegs"), "-rom", "/h/ROM.01", "-s7d1", "/h/gsos.hdv"]


def test_gsplus_output_is_discarded(tmp_path):
    # Catches: GSplus's per-access log (about 400 MB a minute) reaching the
    # launcher's journal or a terminal.
    binary = fake_gsplus(tmp_path, 'echo "UNIMP WRITE to addr 00e0c0c4"\necho "noise" >&2\n')
    result = subprocess.run([str(WRAPPER)], stdin=subprocess.DEVNULL, capture_output=True, text=True,
                            env=env_for(tmp_path, binary), check=True, timeout=10)
    assert result.stdout == "" and result.stderr == ""


def test_the_wrapper_logs_the_exit_so_the_led_state_can_be_checked(tmp_path):
    # Catches: no record that GSplus ended and the LED was turned off.
    binary = fake_gsplus(tmp_path, "exit 0\n")
    subprocess.run([str(WRAPPER)], stdin=subprocess.DEVNULL, env=env_for(tmp_path, binary),
                   check=True, timeout=10)
    log = (tmp_path / "gsplus-run-with-led.log").read_text()
    assert "GSplus exited" in log and log.rstrip().endswith("LED off")


def test_the_exit_is_logged_even_when_gsplus_ends_with_an_error_status(tmp_path):
    # Catches: set -e aborting the wrapper before it logs the exit when GSplus
    # is stopped by a signal or fails (the log then ended at "LED on").
    binary = fake_gsplus(tmp_path, "exit 143\n")
    result = subprocess.run([str(WRAPPER)], stdin=subprocess.DEVNULL, env=env_for(tmp_path, binary),
                            timeout=10)
    log = (tmp_path / "gsplus-run-with-led.log").read_text()
    assert "GSplus exited (status 143)" in log
    assert log.rstrip().endswith("LED off")
    assert result.returncode == 143


WATCHER = Path(__file__).resolve().parent.parent / "lisa-power-button-watcher.sh"


def test_the_power_button_closes_gsplus_by_window_class_not_by_a_keystroke():
    # Catches: the hook going back to sending Alt+F4, which depends on which
    # window has keyboard focus, or to a close that is not the tested one.
    text = WATCHER.read_text()
    branch = text.split("pgrep -x gsplus", 1)[1].split("elif", 1)[0]
    assert "wmctrl -x -c gsplus.gsplus" in branch
    assert "alt+F4" not in branch


def fake_xbindkeys(bin_dir, out_dir):
    """A stand-in xbindkeys: records its config and pid, then stays alive."""
    script = bin_dir / "xbindkeys"
    script.write_text(
        "#!/bin/sh\n"
        'while [ $# -gt 0 ]; do [ "$1" = "-f" ] && cp "$2" "' + str(out_dir) + '/xb.cfg"; shift; done\n'
        'echo $$ > "' + str(out_dir) + '/xb.pid"\n'
        'touch "' + str(out_dir) + '/xb.started"\n'
        "exec sleep 60\n")
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def env_with_path(tmp_path, binary, bin_dir):
    env = env_for(tmp_path, binary)
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return env


def test_f12_closes_gsplus_while_it_runs_and_the_key_helper_is_stopped_afterwards(tmp_path):
    # Catches: no F12 quit (unlike LisaEm and LinApple), F12 closing the wrong
    # thing, the helper not running while GSplus does, or the helper being left
    # running after GSplus exits (it would then keep F12 grabbed for every
    # other emulator).
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_xbindkeys(bin_dir, tmp_path)
    seen = tmp_path / "seen"
    binary = fake_gsplus(
        tmp_path,
        f'for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do '
        f'[ -e "{tmp_path}/xb.started" ] && break; sleep 0.1; done\n'
        f'[ -e "{tmp_path}/xb.started" ] && echo helper-was-running > "{seen}"\n')
    subprocess.run([str(WRAPPER)], stdin=subprocess.DEVNULL, env=env_with_path(tmp_path, binary, bin_dir),
                   check=True, timeout=20)
    assert seen.read_text().strip() == "helper-was-running"
    config = (tmp_path / "xb.cfg").read_text()
    assert "wmctrl -x -c gsplus.gsplus" in config
    assert "F12" in config
    pid = int((tmp_path / "xb.pid").read_text())
    for _ in range(30):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        import time
        time.sleep(0.1)
    else:
        os.kill(pid, 9)
        raise AssertionError("the key helper was still running after GSplus exited")


def test_gsplus_still_runs_when_the_key_helper_is_not_installed(tmp_path):
    # Catches: a machine without xbindkeys failing to start GSplus at all.
    out = tmp_path / "ran"
    binary = fake_gsplus(tmp_path, f'echo yes > "{out}"\n')
    env = env_for(tmp_path, binary)
    env["PATH"] = "/usr/bin:/bin"          # no xbindkeys here
    subprocess.run([str(WRAPPER)], stdin=subprocess.DEVNULL, env=env, check=True, timeout=10)
    assert out.read_text().strip() == "yes"
