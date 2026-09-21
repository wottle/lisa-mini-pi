"""Drives the ~1-2 second boot-diagnostic animation before the picker
appears: a reverse-video highlight sweeps across a fixed list of items
(CPU / MEM / I/O / DISK), leaving a checkmark on each as it "completes"."""


class BootDiagnostic:
    def __init__(self, items: list[str], step_seconds: float):
        self._items = items
        self._step_seconds = step_seconds
        self._elapsed = 0.0
        self._completed: set[int] = set()

    def update(self, dt: float) -> None:
        if self.done:
            return
        self._elapsed += dt
        while (
            not self.done
            and self._elapsed >= self._step_seconds
        ):
            self._elapsed -= self._step_seconds
            self._completed.add(self._current_index_raw())

    def _current_index_raw(self) -> int:
        return len(self._completed)

    @property
    def done(self) -> bool:
        return len(self._completed) >= len(self._items)

    @property
    def current_index(self) -> int:
        if self.done:
            return -1
        return self._current_index_raw()

    @property
    def completed(self) -> set[int]:
        return set(self._completed)

    @property
    def items(self) -> list[str]:
        return list(self._items)
