from PIL import Image

import theme
from gen_icons import (
    ICON_SIZE,
    _DRAW_SIZE,
    draw_macintosh,
    draw_lisa,
    draw_next,
    draw_apple2,
    draw_ibmpc,
    draw_diag_cpu,
    draw_diag_mem,
    draw_diag_io,
    draw_diag_expansion,
    draw_check,
)

ALL_DRAWERS = [
    draw_macintosh, draw_lisa, draw_next, draw_apple2, draw_ibmpc,
    draw_diag_cpu, draw_diag_mem, draw_diag_io, draw_diag_expansion,
    draw_check,
]


def test_every_icon_is_correct_size_and_mode():
    # Drawer functions return their native hand-tuned-coordinate size;
    # main() resizes to theme.ICON_SIZE on the way out (covered by
    # test_main_writes_all_icon_files below).
    for drawer in ALL_DRAWERS:
        image = drawer()
        assert image.size == (_DRAW_SIZE, _DRAW_SIZE)
        assert image.mode == "1"


def test_every_icon_has_at_least_one_black_pixel():
    for drawer in ALL_DRAWERS:
        image = drawer()
        pixels = list(image.getdata())
        assert 0 in pixels, f"{drawer.__name__} produced an all-white icon"


def test_main_writes_all_icon_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import gen_icons

    gen_icons.main()

    expected_files = [
        "macintosh.png", "lisa.png", "next.png", "apple2.png", "ibmpc.png",
        "diag_cpu.png", "diag_mem.png", "diag_io.png", "diag_expansion.png",
    ]
    for filename in expected_files:
        path = tmp_path / "icons" / filename
        assert path.exists(), f"missing {filename}"
        with Image.open(path) as img:
            assert img.size == (ICON_SIZE, ICON_SIZE)

    check_path = tmp_path / "icons" / "check.png"
    assert check_path.exists(), "missing check.png"
    with Image.open(check_path) as img:
        assert img.size == (theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE)
