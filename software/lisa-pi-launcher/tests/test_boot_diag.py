from boot_diag import BootDiagnostic


def test_starts_on_first_item_with_nothing_completed():
    diag = BootDiagnostic(items=["CPU", "MEM", "I/O", "DISK"], step_seconds=0.5)

    assert diag.current_index == 0
    assert diag.completed == set()
    assert diag.done is False


def test_advances_to_next_item_after_step_duration():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.5)

    assert diag.current_index == 1
    assert diag.completed == {0}
    assert diag.done is False


def test_partial_time_does_not_advance():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.3)

    assert diag.current_index == 0
    assert diag.completed == set()


def test_finishes_after_all_items_complete():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.5)
    diag.update(0.5)

    assert diag.done is True
    assert diag.current_index == -1
    assert diag.completed == {0, 1}


def test_accumulates_partial_updates_across_calls():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.3)
    diag.update(0.3)  # total 0.6s, past the 0.5s step boundary

    assert diag.current_index == 1
    assert diag.completed == {0}
