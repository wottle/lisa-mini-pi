"""Tests for the per-machine auto-start setting.

Everything here uses real files in a temporary directory. The boot id is a
real file too, standing in for /proc/sys/kernel/random/boot_id (which is
the one thing a test can't change).
"""

import pytest

from autostart import AutoStart

KNOWN = ["lisa", "macintosh6", "macintosh", "next", "apple2"]


@pytest.fixture
def boot(tmp_path):
    """The fake boot-id file; call it with a string to 'reboot' the machine."""
    path = tmp_path / "boot_id"
    path.write_text("boot-A\n")

    def set_id(value):
        path.write_text(value + "\n")

    set_id.path = path
    return set_id


@pytest.fixture
def store(tmp_path, boot):
    return AutoStart(tmp_path / "cfg", boot_id_path=boot.path)


def new_store(tmp_path, boot):
    """A brand-new object over the same files: what a relaunched launcher sees."""
    return AutoStart(tmp_path / "cfg", boot_id_path=boot.path)


# --- marking -----------------------------------------------------------------

def test_nothing_is_marked_on_a_fresh_machine(store):
    # Catches: a missing settings file crashing, or a default emulator appearing.
    assert store.get() is None


def test_the_mark_survives_a_relaunch(tmp_path, boot, store):
    # Catches: the mark living only in memory, so a reboot forgets it.
    store.toggle("lisa")
    assert new_store(tmp_path, boot).get() == "lisa"


@pytest.mark.parametrize(
    "presses, expected",
    [
        (["lisa"], "lisa"),                    # marks it
        (["lisa", "lisa"], None),              # same one again clears it
        (["lisa", "next"], "next"),            # another one moves the mark (never two)
        (["lisa", "next", "next"], None),      # and that one clears too
        (["lisa", "lisa", "lisa"], "lisa"),    # clear then mark again
    ],
)
def test_toggle_marks_clears_and_moves_the_single_mark(store, presses, expected):
    # Catches: allowing two marks, not clearing on a repeat press, or not
    # moving the mark when another system is chosen.
    result = None
    for system_id in presses:
        result = store.toggle(system_id)
    assert result == expected
    assert store.get() == expected


@pytest.mark.parametrize("junk", [b"", b"  \n", b"\xff\xfe\x00"])
def test_a_damaged_settings_file_means_not_set(tmp_path, store, junk):
    # Catches: a corrupt or empty file crashing the launcher at start-up.
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / "autostart").write_bytes(junk)
    assert store.get() is None


def test_a_settings_folder_that_cannot_be_written_does_not_crash_the_key(tmp_path, boot):
    # Catches: pressing A on a read-only or broken card raising inside the
    # main loop. Here the settings folder's path is occupied by a plain file.
    (tmp_path / "cfg").write_text("in the way")
    broken = AutoStart(tmp_path / "cfg", boot_id_path=boot.path)
    assert broken.toggle("lisa") is None
    assert broken.get() is None


# --- starting up: once per power-on -------------------------------------------

def test_the_first_start_of_a_boot_launches_the_marked_system(store):
    # Catches: auto-start never firing, or returning the wrong system.
    store.toggle("next")
    assert store.startup(KNOWN) == "next"


def test_a_restart_in_the_same_boot_does_not_launch_it_again(tmp_path, boot, store):
    # Catches the core requirement: a watchdog restart or a return from the
    # desktop retrying a possibly broken emulator in a loop.
    store.toggle("lisa")
    assert store.startup(KNOWN) == "lisa"
    assert new_store(tmp_path, boot).startup(KNOWN) is None


def test_marking_after_the_launcher_is_running_does_not_launch_on_a_later_restart(tmp_path, boot, store):
    # Catches: only noting the boot when auto-start fires. Here the launcher
    # started with nothing marked, I mark a system, then the launcher restarts
    # in the same boot: it must still show the picker.
    assert store.startup(KNOWN) is None
    store.toggle("lisa")
    assert new_store(tmp_path, boot).startup(KNOWN) is None


def test_the_next_boot_launches_it_again(tmp_path, boot, store):
    # Catches: a once-only flag that a new power-on never resets.
    store.toggle("lisa")
    assert store.startup(KNOWN) == "lisa"
    boot("boot-B")
    assert new_store(tmp_path, boot).startup(KNOWN) == "lisa"


def test_a_marked_system_that_is_no_longer_configured_is_ignored(store):
    # Catches: trying to launch a system that was removed from config.json.
    store.toggle("gone")
    assert store.startup(KNOWN) is None


def test_no_readable_boot_id_means_no_auto_start(tmp_path):
    # Catches: auto-starting when "once per boot" can't be guaranteed (for
    # example a development machine with no /proc).
    s = AutoStart(tmp_path / "cfg", boot_id_path=tmp_path / "does-not-exist")
    s.toggle("lisa")
    assert s.startup(KNOWN) is None


def test_if_the_boot_cannot_be_noted_it_does_not_auto_start(tmp_path, boot, store):
    # Catches: launching when the "already tried this boot" note can't be
    # written, which would allow a loop. Here the note's path is a directory.
    store.toggle("lisa")
    (tmp_path / "cfg" / "last-boot-id").mkdir()
    assert store.startup(KNOWN) is None
