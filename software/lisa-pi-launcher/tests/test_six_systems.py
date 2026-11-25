"""A sixth system wraps the picker onto a second row; everything still has
to fit on the screen, footer included."""

import contextlib
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import pytest
import theme
from rendering import (
    ItemVisual,
    footer_auto_hint_rect,
    footer_layout,
    hit_test,
    item_layout,
    panel_interior_rect,
    render_frame,
)

SIZES = [(1024, 768), (2048, 1536)]


@contextlib.contextmanager
def scaled(width, height):
    try:
        yield theme.apply_scale(width, height)
    finally:
        theme.apply_scale(1024, 768)


def items(count):
    icon = pygame.Surface((theme.ICON_SIZE, theme.ICON_SIZE))
    icon.fill((255, 255, 255))
    return [ItemVisual(icon=icon, label=f"S{i}", status_icon=None,
                       selected=(i == 0), subtitle="SUB") for i in range(count)]


@pytest.mark.parametrize("size", SIZES)
def test_six_systems_fit_on_the_screen_with_the_footer(size):
    # Catches: the second row pushing the footer (SELECT/START/AUTO hints and
    # the SHUT DOWN/QUIT buttons) off the bottom of the screen.
    with scaled(*size):
        its = items(6)
        screen = pygame.Rect(0, 0, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)
        for card in item_layout(its):
            assert screen.contains(card)
        for button in footer_layout(its).values():
            assert screen.contains(button)
        assert screen.contains(footer_auto_hint_rect(its))
        interior = panel_interior_rect(row_count=2)
        assert interior.top - theme.PANEL_CONTENT_INSET >= 0
        assert interior.bottom + theme.PANEL_CONTENT_INSET + theme.SHADOW_OFFSET <= theme.SCREEN_HEIGHT


@pytest.mark.parametrize("size", SIZES)
def test_the_two_row_panel_is_centred_vertically(size):
    # Catches: the panel staying where a one-row panel would sit.
    with scaled(*size):
        interior = panel_interior_rect(row_count=2)
        top = interior.top - theme.PANEL_CONTENT_INSET
        bottom = interior.bottom + theme.PANEL_CONTENT_INSET
        assert abs(top - (theme.SCREEN_HEIGHT - bottom)) <= 1


def test_five_systems_stay_exactly_where_they_were():
    # Catches: the fix moving the existing one-row layout. The numbers are
    # the design values, stated by hand: a 395 px panel centred in 768 px.
    assert panel_interior_rect(row_count=1).top == 186 + theme.PANEL_CONTENT_INSET
    assert item_layout(items(5))[0].top == 274


def test_the_sixth_card_can_be_clicked():
    # Catches: the second row's card not being reachable by mouse.
    its = items(6)
    cards = item_layout(its)
    assert len(cards) == 6
    assert hit_test(its, cards[5].center) == 5
    assert hit_test(its, cards[0].center) == 0


def test_a_six_system_frame_draws_without_error():
    # Catches: a crash drawing the two-row layout.
    screen = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))
    render_frame(screen, "CHOOSE YOUR ADVENTURE", items(6))
