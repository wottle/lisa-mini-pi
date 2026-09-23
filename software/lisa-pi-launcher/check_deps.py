"""Startup dependency check: verifies the binaries, ROM/disk assets, and
system integration files this kiosk needs are actually present, and logs
clear pass/fail results to a dedicated log file.

Deliberately non-blocking and dependency-free (stdlib only, no pygame/PIL
import) - it must be able to run and report clearly even when something
as basic as pygame itself is broken, and a missing optional asset (e.g.
one emulator's ROM) shouldn't stop the whole kiosk from booting into
whatever *does* work. Run standalone any time:

    python3 check_deps.py

xsession-launcher.sh also runs it once at the start of every kiosk
session, appending to ~/lisa-mini-pi-dependency-check.log - check that
file first when something that used to work stops working after moving
to a new Pi or a fresh setup.
"""

import json
import os
import shutil
import sys
from datetime import datetime

LOG_PATH = os.path.expanduser("~/lisa-mini-pi-dependency-check.log")

# Commands the kiosk session and its helper scripts assume are on PATH,
# each with a one-line note on what actually breaks if it's missing.
_REQUIRED_COMMANDS = {
    "openbox": "kiosk session's window manager (xsession-launcher.sh)",
    "xinit": "starts the kiosk's X session (launcher.service)",
    "python3": "runs the launcher itself",
    "gio": "trusts the desktop 'Emulator Launcher' icon (SETUP.md §7)",
}

# Present on some Pis but not others depending on what's actually wired
# up (GPIO hardware, F12 power-button hotkey) - reported as warnings, not
# failures, since a Pi without the GPIO button legitimately doesn't need
# them.
_OPTIONAL_COMMANDS = {
    "pinctrl": "GPIO LED/button control (lisa-run-with-led.sh, the power-button watcher)",
    "gpiomon": "GPIO button edge detection (lisa-power-button-watcher.sh)",
    "xdotool": "sends LisaEm's F12 power-button hotkey (lisa-power-button-watcher.sh)",
}

_SYSTEMD_UNITS = [
    "/etc/systemd/system/launcher.service",
    "/etc/systemd/system/launcher-watchdog.service",
    "/etc/systemd/system/launcher-watchdog.timer",
]

_POLKIT_RULE = "/etc/polkit-1/rules.d/10-lisa-launcher-power.rules"


def _log(lines: list[str]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"=== dependency check {timestamp} ===\n")
        for line in lines:
            f.write(line + "\n")
        f.write("\n")


def _check_commands(required: dict[str, str], severity: str) -> list[str]:
    results = []
    for command, note in required.items():
        found = shutil.which(command)
        status = "ok" if found else severity
        detail = found if found else f"not found on PATH - needed for: {note}"
        results.append(f"[{status.upper():4}] command {command}: {detail}")
    return results


def _check_config_json_paths(config_path: str) -> list[str]:
    results = []
    try:
        with open(config_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return [f"[FAIL] could not read/parse {config_path}: {e}"]

    for system in data.get("systems", []):
        system_id = system.get("id", "?")
        command = system.get("command", [])
        for arg in command:
            # Only check things that look like absolute filesystem paths -
            # skip flags (-k, -d, ...) and bare command names resolved via
            # PATH (those go through _check_commands instead).
            if not isinstance(arg, str) or not arg.startswith("/"):
                continue
            if os.path.exists(arg):
                executable_note = "" if not command[0] == arg or os.access(arg, os.X_OK) else " (not executable)"
                results.append(f"[OK  ] {system_id}: {arg} exists{executable_note}")
            else:
                results.append(f"[FAIL] {system_id}: {arg} does not exist - config.json references a missing file")

        icon = system.get("icon")
        if icon and not os.path.exists(icon):
            results.append(f"[FAIL] {system_id}: icon {icon} does not exist")
    return results


def _check_paths(paths: list[str], label: str) -> list[str]:
    results = []
    for path in paths:
        status = "OK  " if os.path.exists(path) else "FAIL"
        results.append(f"[{status}] {label} {path}")
    return results


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")

    all_results = []
    all_results += _check_commands(_REQUIRED_COMMANDS, "fail")
    all_results += _check_commands(_OPTIONAL_COMMANDS, "warn")
    all_results += _check_config_json_paths(config_path)
    all_results += _check_paths(_SYSTEMD_UNITS, "systemd unit")
    all_results += _check_paths([_POLKIT_RULE], "polkit rule")

    for line in all_results:
        print(line)

    _log(all_results)
    print(f"\nFull log: {LOG_PATH}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
