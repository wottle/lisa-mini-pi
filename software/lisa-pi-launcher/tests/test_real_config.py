"""The committed config.json itself: every system it lists must be launchable
as shipped (icon present, launch script present and executable)."""

import os
from pathlib import Path

import pytest
from PIL import Image

import theme
from config import load_config

LAUNCHER_DIR = Path(__file__).resolve().parent.parent
SYSTEMS = load_config(str(LAUNCHER_DIR / "config.json"))
IN_REPO = "lisa-mini-pi/software/lisa-pi-launcher/"


def test_the_launcher_lists_six_systems_with_unique_ids():
    # Catches: a system missing from the picker, or two sharing an id (the
    # auto-start mark is stored by id).
    ids = [s.id for s in SYSTEMS]
    assert ids == ["lisa", "macintosh6", "macintosh", "next", "apple2", "apple2gs"]
    assert len(set(ids)) == len(ids)


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.id)
def test_each_systems_icon_exists_at_the_picker_icon_size(system):
    # Catches: a card with no picture, or a picture the launcher would
    # have to stretch.
    icon = LAUNCHER_DIR / system.icon
    assert icon.is_file(), icon
    assert Image.open(icon).size == (theme.ICON_SIZE, theme.ICON_SIZE)


@pytest.mark.parametrize("system", SYSTEMS, ids=lambda s: s.id)
def test_each_systems_launch_script_in_the_repo_exists_and_is_executable(system):
    # Catches: a config entry pointing at a script that was never added or
    # lost its executable bit, which fails only when someone clicks it.
    program = system.command[0]
    if IN_REPO not in program:
        pytest.skip("launches a system binary, not a script in this repo")
    script = LAUNCHER_DIR / program.split(IN_REPO, 1)[1]
    assert script.is_file(), script
    assert os.access(script, os.X_OK), script


def test_the_iigs_entry_passes_its_rom_and_disk_under_the_home_folder():
    # Catches: GSplus starting with no ROM or disk (it would sit at a
    # "Check startup device" screen), or hardcoding one user's folder.
    entry = next(s for s in SYSTEMS if s.id == "apple2gs")
    cmd = entry.command
    home = os.path.expanduser("~")
    assert cmd[cmd.index("-rom") + 1] == f"{home}/ROM.01"
    assert cmd[cmd.index("-s7d1") + 1] == f"{home}/gsos.hdv"
