from redraw import RedrawGate


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def test_first_call_draws():
    assert RedrawGate(clock=FakeClock()).should_draw("a") is True


def test_unchanged_state_does_not_redraw_within_the_refresh_interval():
    clock = FakeClock()
    gate = RedrawGate(refresh_seconds=1.0, clock=clock)
    assert gate.should_draw(("sel", 0)) is True
    for _ in range(100):  # ~3 s of 30 fps, but we stay inside the first second
        clock.now += 0.009
        assert gate.should_draw(("sel", 0)) is False


def test_changed_state_redraws_immediately():
    clock = FakeClock()
    gate = RedrawGate(clock=clock)
    gate.should_draw(("sel", 0))
    clock.now += 0.01
    assert gate.should_draw(("sel", 1)) is True
    clock.now += 0.01
    assert gate.should_draw(("sel", 1)) is False


def test_safety_refresh_fires_once_per_interval_when_nothing_changes():
    clock = FakeClock()
    gate = RedrawGate(refresh_seconds=1.0, clock=clock)
    draws = 0
    for _ in range(300):  # 10 s at 30 fps, state never changes
        clock.now += 1 / 30
        draws += gate.should_draw("same")
    # first draw + roughly one per second
    assert 9 <= draws <= 12


def test_invalidate_forces_a_redraw_even_if_state_is_unchanged():
    clock = FakeClock()
    gate = RedrawGate(clock=clock)
    gate.should_draw("same")
    clock.now += 0.01
    assert gate.should_draw("same") is False
    gate.invalidate()
    assert gate.should_draw("same") is True
    assert gate.should_draw("same") is False
