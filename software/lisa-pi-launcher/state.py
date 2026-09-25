"""The selection state machine: which system is highlighted, and whether
we're idly selecting or currently launching one."""

from enum import Enum, auto

from config import SystemEntry


class Phase(Enum):
    SELECTING = auto()
    STARTING = auto()


class LauncherState:
    def __init__(self, systems: list[SystemEntry]):
        if not systems:
            raise ValueError("LauncherState requires at least one system")
        self._systems = systems
        self._selected_index = 0
        self._phase = Phase.SELECTING

    def move_selection(self, delta: int) -> None:
        self.select_index(self._selected_index + delta)

    def select_index(self, index: int) -> None:
        """Sets the selection directly (clamped) - used by mouse hover/
        click selection, where the target index comes from a hit test
        rather than a relative +1/-1 move."""
        self._selected_index = max(0, min(len(self._systems) - 1, index))

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def selected(self) -> SystemEntry:
        return self._systems[self._selected_index]

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def systems(self) -> list[SystemEntry]:
        return list(self._systems)

    def start_selected(self) -> None:
        self._phase = Phase.STARTING

    def finish_starting(self) -> None:
        self._phase = Phase.SELECTING

    def header_text(self) -> str:
        if self._phase == Phase.STARTING:
            return f"STARTING {self.selected.name}..."
        return "CHOOSE YOUR ADVENTURE"
