import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from bitmap_font import render_text, text_size, CHAR_WIDTH, CHAR_HEIGHT


def test_text_size_scales_with_character_count_and_scale():
    assert text_size("AB", scale=1) == (CHAR_WIDTH * 2 + 1, CHAR_HEIGHT)
    assert text_size("AB", scale=2) == ((CHAR_WIDTH * 2 + 1) * 2, CHAR_HEIGHT * 2)


def test_text_size_empty_string_is_zero():
    assert text_size("", scale=1) == (0, CHAR_HEIGHT)


def test_render_text_draws_black_pixels_on_white_surface():
    surface = pygame.Surface((64, 16))
    surface.fill((255, 255, 255))

    rect = render_text(surface, "A", 0, 0, scale=1, color=(0, 0, 0))

    assert rect.width == CHAR_WIDTH
    assert rect.height == CHAR_HEIGHT
    black_pixels = sum(
        1
        for px in range(rect.width)
        for py in range(rect.height)
        if surface.get_at((px, py))[:3] == (0, 0, 0)
    )
    assert black_pixels > 0


def test_render_text_unknown_character_renders_as_blank_cell():
    surface = pygame.Surface((64, 16))
    surface.fill((255, 255, 255))

    # '@' is not in the font table - should not raise, should occupy a
    # blank cell the width of one character.
    rect = render_text(surface, "@", 0, 0, scale=1, color=(0, 0, 0))

    assert rect.width == CHAR_WIDTH
