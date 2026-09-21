import glob
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import theme
from rendering import (
    ItemVisual,
    _item_footprint,
    draw_checkerboard,
    draw_checkerboard_cached,
    draw_panel,
    draw_item,
    draw_top_strip,
    hit_test,
    item_layout,
    render_frame,
)


def _make_icon(color=(0, 0, 0)) -> pygame.Surface:
    icon = pygame.Surface((theme.ICON_SIZE, theme.ICON_SIZE))
    icon.fill((255, 255, 255))
    icon.fill(color, pygame.Rect(2, 2, theme.ICON_SIZE - 4, theme.ICON_SIZE - 4))
    return icon


def _make_screen() -> pygame.Surface:
    return pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))


def test_draw_checkerboard_alternates_black_and_white_at_requested_cell_size():
    cell_size = 4
    surface = pygame.Surface((cell_size * 4, cell_size * 4))

    draw_checkerboard(surface, cell_size)

    # Sample the center of each of the first two cells on the top row -
    # they must differ, and both must be pure black or white (no gray/
    # antialiasing, matching the project's 1-bit rendering constraint).
    first = surface.get_at((cell_size // 2, cell_size // 2))[:3]
    second = surface.get_at((cell_size + cell_size // 2, cell_size // 2))[:3]
    assert {first, second} == {(0, 0, 0), (255, 255, 255)}
    # A pixel one cell down and one cell over (diagonal neighbor) matches
    # the first cell's color - confirms a checkerboard, not stripes.
    diagonal = surface.get_at((cell_size + cell_size // 2, cell_size + cell_size // 2))[:3]
    assert diagonal == first


def test_draw_checkerboard_cached_reuses_same_size_rebuilds_on_resize():
    surface_a = pygame.Surface((16, 16))
    draw_checkerboard_cached(surface_a, 4)
    color_a = surface_a.get_at((0, 0))[:3]

    # A different-sized surface must still get a correctly-drawn pattern,
    # not a stale cached image from the first size silently blitted in.
    surface_b = pygame.Surface((8, 8))
    draw_checkerboard_cached(surface_b, 4)

    assert surface_b.get_size() == (8, 8)
    colors_b = {surface_b.get_at((x, y))[:3] for x in range(8) for y in range(8)}
    assert colors_b == {(0, 0, 0), (255, 255, 255)}


def test_draw_panel_returns_interior_rect_within_panel_bounds():
    surface = _make_screen()
    surface.fill((0, 0, 0))

    interior = draw_panel(surface)

    assert interior.left >= theme.PANEL_X
    assert interior.top >= theme.PANEL_Y
    assert interior.right <= theme.PANEL_X + theme.PANEL_WIDTH
    assert interior.bottom <= theme.PANEL_Y + theme.PANEL_HEIGHT
    # interior of the panel must be white
    assert surface.get_at((interior.left + 1, interior.top + 1))[:3] == (255, 255, 255)


def test_draw_item_selected_fills_area_black():
    surface = _make_screen()
    surface.fill((255, 255, 255))
    item = ItemVisual(icon=_make_icon(), label="MEM", status_icon=None, selected=True)

    draw_item(surface, center_x=200, top_y=40, item=item)

    # somewhere in the item's footprint there should be a black background
    # pixel from the reverse-video fill (not just the icon's own black
    # pixels, which a non-selected icon would also have). Derive the
    # actual footprint from the real layout function rather than
    # hardcoding geometry that would silently drift out of sync with
    # theme.py's icon/spacing constants.
    footprint = _item_footprint(center_x=200, top_y=40, item=item)
    black_background_found = any(
        surface.get_at((x, y))[:3] == (0, 0, 0)
        for x in range(footprint.left, footprint.left + 5)
        for y in range(footprint.top, footprint.top + 5)
    )
    assert black_background_found


def test_top_strip_is_white():
    surface = _make_screen()
    surface.fill((0, 0, 0))  # anything other than white, to prove draw_top_strip actually paints it

    draw_top_strip(surface)

    # A pixel near the left edge of the strip (away from the right-aligned
    # status glyph) should be plain white.
    assert surface.get_at((2, 0))[:3] == (255, 255, 255)
    assert surface.get_at((2, theme.TOP_STRIP_HEIGHT - 1))[:3] == (255, 255, 255)


def test_top_strip_spans_the_full_surface_width():
    # draw_top_strip takes its width from the surface it's given (there's
    # no fixed logical-canvas width anymore) - confirm it actually fills
    # a surface of a different width than theme.SCREEN_WIDTH.
    surface = pygame.Surface((200, theme.TOP_STRIP_HEIGHT))
    surface.fill((0, 0, 0))

    draw_top_strip(surface)

    assert surface.get_at((199, 0))[:3] == (255, 255, 255)


def test_render_frame_draws_top_strip():
    surface = _make_screen()
    render_frame(surface, "SELECT SYSTEM...", "", [])
    assert surface.get_at((2, 0))[:3] == (255, 255, 255)


def test_real_shipped_icons_match_theme_icon_size():
    # Regression test for the theme.ICON_SIZE (20) vs gen_icons.ICON_SIZE (24)
    # mismatch: draw_item builds its icon_rect from theme.ICON_SIZE, but
    # pygame's blit() only uses a dest rect's topleft, silently ignoring
    # any size mismatch with the source surface. A synthetic icon sized to
    # theme.ICON_SIZE (like _make_icon above) can never catch that drift -
    # only loading a real shipped asset can.
    icon_paths = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "icons", "*.png")))
    assert icon_paths, "expected at least one real icon under icons/ to check against"
    for path in icon_paths:
        icon = pygame.image.load(path)
        # check.png is deliberately smaller - a status badge, not a
        # full item icon - see theme.CHECK_ICON_SIZE.
        expected_size = (
            (theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE)
            if os.path.basename(path) == "check.png"
            else (theme.ICON_SIZE, theme.ICON_SIZE)
        )
        assert icon.get_size() == expected_size, (
            f"{path} is {icon.get_size()}, but expected {expected_size}"
        )


def test_checkerboard_survives_under_render_frame():
    # render_frame draws directly onto whatever's already on the surface
    # (no separate logical surface/colorkey compositing step anymore) -
    # a checkerboard drawn first should still show through everywhere
    # render_frame doesn't paint over (i.e. away from the panel).
    surface = _make_screen()
    draw_checkerboard_cached(surface, 4)
    render_frame(surface, "SELECT SYSTEM...", "", [])

    corner_y = surface.get_height() - 20
    samples = {surface.get_at((x, corner_y))[:3] for x in range(0, 40)}
    assert samples == {(0, 0, 0), (255, 255, 255)}


def test_item_layout_matches_what_render_frame_actually_draws():
    # Regression guard against the layout drifting between drawing and
    # hit-testing: wherever item_layout() says an item's footprint is,
    # that's where render_frame's reverse-video fill for the selected
    # item must actually be.
    items = [
        ItemVisual(icon=_make_icon(), label="LISA", status_icon=None, selected=True),
        ItemVisual(icon=_make_icon(), label="MACINTOSH", status_icon=None, selected=False),
    ]
    surface = _make_screen()
    render_frame(surface, "SELECT SYSTEM...", "", items)

    footprints = item_layout(items)
    assert len(footprints) == 2

    selected_footprint = footprints[0]
    corner = (selected_footprint.left + 2, selected_footprint.top + 2)
    assert surface.get_at(corner)[:3] == (0, 0, 0), (
        "item_layout()'s footprint for the selected item should be black "
        "(reverse video), matching where render_frame actually drew it"
    )


def test_hit_test_returns_index_of_item_under_point_or_none():
    items = [
        ItemVisual(icon=_make_icon(), label="LISA", status_icon=None, selected=True),
        ItemVisual(icon=_make_icon(), label="MACINTOSH", status_icon=None, selected=False),
    ]
    footprints = item_layout(items)

    assert hit_test(items, footprints[0].center) == 0
    assert hit_test(items, footprints[1].center) == 1
    assert hit_test(items, (0, 0)) is None


def test_item_layout_empty_for_no_items():
    assert item_layout([]) == []


def test_render_frame_runs_without_error_with_multiple_items():
    surface = _make_screen()
    items = [
        ItemVisual(icon=_make_icon(), label="LISA", status_icon=None, selected=True),
        ItemVisual(icon=_make_icon(), label="MACINTOSH", status_icon=None, selected=False),
    ]

    render_frame(surface, "SELECT SYSTEM...", "LISA / OFFICE SYSTEM 3.1", items)
    # no exception is the primary assertion; also sanity-check something
    # was actually drawn (not a blank surface).
    colors = {surface.get_at((x, y))[:3] for x in range(0, theme.SCREEN_WIDTH, 10) for y in range(0, theme.SCREEN_HEIGHT, 10)}
    assert len(colors) > 1
