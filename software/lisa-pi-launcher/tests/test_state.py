import pytest
from config import SystemEntry
from state import LauncherState, Phase

LISA = SystemEntry(id="lisa", name="LISA", subtitle="OFFICE SYSTEM 3.1", icon="icons/lisa.png", command=["true"])
MAC = SystemEntry(id="mac", name="MACINTOSH", subtitle="SYSTEM 7.5.5", icon="icons/macintosh.png", command=["true"])


def test_starts_selecting_first_system():
    state = LauncherState([LISA, MAC])

    assert state.phase == Phase.SELECTING
    assert state.selected_index == 0
    assert state.selected == LISA


def test_move_selection_right_advances():
    state = LauncherState([LISA, MAC])

    state.move_selection(1)

    assert state.selected_index == 1
    assert state.selected == MAC


def test_move_selection_clamps_at_last_item():
    state = LauncherState([LISA, MAC])

    state.move_selection(1)
    state.move_selection(1)

    assert state.selected_index == 1


def test_move_selection_clamps_at_first_item():
    state = LauncherState([LISA, MAC])

    state.move_selection(-1)

    assert state.selected_index == 0


def test_start_selected_moves_to_starting_phase():
    state = LauncherState([LISA, MAC])

    state.start_selected()

    assert state.phase == Phase.STARTING


def test_finish_starting_returns_to_selecting():
    state = LauncherState([LISA, MAC])
    state.start_selected()

    state.finish_starting()

    assert state.phase == Phase.SELECTING


def test_panel_lines_while_selecting():
    state = LauncherState([LISA, MAC])

    assert state.panel_lines() == ("SELECT SYSTEM...", "LISA / OFFICE SYSTEM 3.1")


def test_panel_lines_while_starting():
    state = LauncherState([LISA, MAC])
    state.start_selected()

    assert state.panel_lines() == ("STARTING...", "STARTING LISA...")


def test_cannot_construct_with_empty_system_list():
    with pytest.raises(ValueError):
        LauncherState([])


def test_select_index_sets_selection_directly():
    state = LauncherState([LISA, MAC])

    state.select_index(1)

    assert state.selected_index == 1
    assert state.selected == MAC


def test_select_index_clamps_above_range():
    state = LauncherState([LISA, MAC])

    state.select_index(5)

    assert state.selected_index == 1


def test_select_index_clamps_below_range():
    state = LauncherState([LISA, MAC])
    state.select_index(1)

    state.select_index(-3)

    assert state.selected_index == 0
