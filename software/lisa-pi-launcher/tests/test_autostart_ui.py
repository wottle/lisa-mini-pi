"""How the auto-start mark looks: the AUTO tag on a card and the footer hint."""

import contextlib
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import theme
from bitmap_font import text_size
from rendering import (
    _FOOTER_CENTER,
    _FOOTER_LEFT,
    ItemVisual,
    auto_tag_rect,
    footer_auto_hint_rect,
    item_layout,
    panel_interior_rect,
    render_frame,
)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)


@contextlib.contextmanager
def scaled(width, height):
    try:
        yield theme.apply_scale(width, height)
    finally:
        theme.apply_scale(1024, 768)


def items(auto_index=None, selected=2):
    icon = pygame.Surface((theme.ICON_SIZE, theme.ICON_SIZE))
    icon.fill(WHITE)
    return [
        ItemVisual(icon=icon, label=f"SYS{i}", status_icon=None,
                   selected=(i == selected), subtitle="SUB", auto=(i == auto_index))
        for i in range(5)
    ]


def frame(its):
    screen = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))
    screen.fill(WHITE)
    render_frame(screen, "CHOOSE YOUR ADVENTURE", its)
    return screen


def corner(screen, rect):
    """A pixel inside the tag's padding, clear of the lettering."""
    return screen.get_at((rect.left + 1, rect.top + 1))[:3]


def test_the_marked_system_shows_a_black_tag_in_its_top_right_corner():
    # Catches: the tag not being drawn, or being drawn on the wrong card.
    its = items(auto_index=0, selected=2)
    screen = frame(its)
    cards = item_layout(its)
    assert corner(screen, auto_tag_rect(cards[0])) == BLACK
    assert corner(screen, auto_tag_rect(cards[1])) == WHITE  # an unmarked card has none


def test_the_tag_stays_visible_when_the_marked_card_is_highlighted():
    # Catches: a black tag on a highlighted (black) card, i.e. invisible.
    its = items(auto_index=0, selected=0)
    screen = frame(its)
    assert corner(screen, auto_tag_rect(item_layout(its)[0])) == WHITE


def test_the_tag_is_in_the_cards_top_right_corner():
    # Catches: the tag drawn in the wrong corner. The expectation is stated
    # by hand (right quarter, top eighth of the card), not computed by the
    # code that places the tag.
    card = item_layout(items(auto_index=0))[0]
    tag = auto_tag_rect(card)
    assert tag.centerx > card.left + 3 * card.width // 4
    assert tag.centery < card.top + card.height // 8


def test_the_tag_sits_inside_the_card_and_clear_of_the_icon():
    # Catches: a layout change pushing the tag over the icon or off the card.
    card = item_layout(items(auto_index=0))[0]
    tag = auto_tag_rect(card)
    assert card.contains(tag)
    assert tag.bottom <= card.top + theme.ITEM_BOX_PADDING_TOP


def test_the_tag_grows_with_the_screen_scale():
    # Catches: the tag's size constants missing from the scaled set, leaving
    # it tiny next to the 2x cards on a 2048x1536 panel.
    its = items(auto_index=0)
    one = auto_tag_rect(item_layout(its)[0])
    with scaled(2048, 1536):
        two = auto_tag_rect(item_layout(items(auto_index=0))[0])
    assert (two.width, two.height) == (2 * one.width, 2 * one.height)


def test_the_footer_hint_sits_in_the_free_gap_and_is_drawn():
    # Catches: the A AUTO hint overlapping the SELECT or START text, or not
    # being drawn at all.
    its = items()
    hint = footer_auto_hint_rect(its)
    interior = panel_interior_rect(1)
    select_end = interior.left + text_size(_FOOTER_LEFT, scale=theme.FONT_SCALE)[0]
    start_begin = interior.centerx - text_size(_FOOTER_CENTER, scale=theme.FONT_SCALE)[0] // 2
    assert select_end < hint.left and hint.right < start_begin

    screen = frame(its)
    dark = sum(
        1
        for x in range(hint.left, hint.right)
        for y in range(hint.top, hint.bottom)
        if screen.get_at((x, y))[:3] == BLACK
    )
    assert dark > 50
