import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from cursor import build_cursor_surface, SIZE


def test_cursor_surface_is_correct_size():
    surface = build_cursor_surface()
    assert surface.get_size() == (SIZE, SIZE)


def test_cursor_surface_has_black_and_white_pixels_only():
    # Matches the project's 1-bit rendering constraint: no antialiasing,
    # no gray, no color - just the arrow's black outline and white fill
    # (plus fully-transparent colorkeyed background pixels, which don't
    # show up in get_at() color comparisons since colorkey only affects
    # blitting, not pixel storage - so this only asserts on the drawn
    # colors that get_at() actually returns).
    surface = build_cursor_surface()
    colors = {
        surface.get_at((x, y))[:3]
        for x in range(SIZE)
        for y in range(SIZE)
    }
    assert colors <= {(0, 0, 0), (255, 255, 255), surface.get_colorkey()[:3]}


def test_cursor_surface_has_visible_content():
    surface = build_cursor_surface()
    pixels = [surface.get_at((x, y))[:3] for x in range(SIZE) for y in range(SIZE)]
    assert (0, 0, 0) in pixels
    assert (255, 255, 255) in pixels
