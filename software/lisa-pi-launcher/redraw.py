"""Decides when the picker actually needs repainting.

Redrawing the whole 2048x1536 frame costs ~17 ms on a Pi 5 (checkerboard
blit + panel + bitmap text), and doing it 30 times a second for a screen
that hasn't changed kept one core near 50% busy while idle. The picker only
needs a repaint when something visible changed, when the window was exposed
(e.g. an emulator window that covered it went away), or - as a cheap safety
net for any repaint we weren't told about - once every `refresh_seconds`.
"""

import time


class RedrawGate:
    def __init__(self, refresh_seconds: float = 1.0, clock=time.monotonic):
        self._refresh = refresh_seconds
        self._clock = clock
        self._last_key = None
        self._last_draw = None  # None => never drawn, so the first call draws

    def invalidate(self) -> None:
        """Force the next should_draw() to return True (window exposed,
        returned from an emulator, or anything else that may have left the
        screen stale)."""
        self._last_draw = None

    def should_draw(self, key) -> bool:
        """`key` is a hashable snapshot of everything that affects the
        picture (selection, header text, phase, hovered buttons...). True
        when it changed since the last draw, a redraw was forced, or the
        safety refresh interval has elapsed. Calling this and getting True
        counts as having drawn."""
        now = self._clock()
        if (
            self._last_draw is None
            or key != self._last_key
            or now - self._last_draw >= self._refresh
        ):
            self._last_key = key
            self._last_draw = now
            return True
        return False
