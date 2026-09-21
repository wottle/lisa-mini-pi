"""Composes the checkerboard background, the diagnostic/selection panel
(with its drop shadow), and the row of icon+label+status items directly
onto the real screen surface - see theme.py for why there's no separate
logical/design surface scaled up to it."""

from dataclasses import dataclass

import pygame

import theme
from bitmap_font import render_text, text_size

_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)

# Cache for the checkerboard: it's fully deterministic for a given surface
# size, so it's built once and blitted from then on rather than redrawing
# every frame. Keyed by size as a staleness guard.
_checker_cache: pygame.Surface | None = None
_checker_cache_size: tuple[int, int] | None = None


@dataclass
class ItemVisual:
    icon: pygame.Surface
    label: str
    status_icon: pygame.Surface | None
    selected: bool


def draw_checkerboard(surface: pygame.Surface, cell_size: int) -> None:
    """Draws an axis-aligned black/white checkerboard directly onto
    `surface`, at `surface`'s own pixel resolution and never through
    pygame.transform.scale, so the pattern's cell boundaries always land
    on exact pixel boundaries and the checkerboard can never alias,
    regardless of the display's actual resolution."""
    width, height = surface.get_size()
    for y in range(0, height, cell_size):
        for x in range(0, width, cell_size):
            color = _BLACK if ((x // cell_size) + (y // cell_size)) % 2 == 0 else _WHITE
            surface.fill(color, pygame.Rect(x, y, cell_size, cell_size))


def draw_checkerboard_cached(surface: pygame.Surface, cell_size: int) -> None:
    global _checker_cache, _checker_cache_size
    size = surface.get_size()
    if _checker_cache is None or _checker_cache_size != size:
        cache = pygame.Surface(size)
        draw_checkerboard(cache, cell_size)
        _checker_cache = cache
        _checker_cache_size = size
    surface.blit(_checker_cache, (0, 0))


def _panel_height(row_count: int) -> int:
    """PANEL_HEIGHT already fits exactly one item row; each additional
    row needs one more ITEM_ROW_HEIGHT plus the gap above it."""
    extra_rows = max(0, row_count - 1)
    return theme.PANEL_HEIGHT + extra_rows * (theme.ITEM_ROW_HEIGHT + theme.ITEMS_ROW_GAP)


def _row_count(item_count: int) -> int:
    if item_count == 0:
        return 1
    return -(-item_count // theme.ITEMS_PER_ROW)  # ceil division


def panel_interior_rect(row_count: int = 1) -> pygame.Rect:
    """The panel's interior content rect, in screen coordinates. Pure
    layout math (no drawing) so it can be reused by both draw_panel and
    mouse hit-testing without them ever drifting apart."""
    panel_rect = pygame.Rect(theme.PANEL_X, theme.PANEL_Y, theme.PANEL_WIDTH, _panel_height(row_count))
    return panel_rect.inflate(-theme.PANEL_CONTENT_INSET, -theme.PANEL_CONTENT_INSET)


def draw_panel(surface: pygame.Surface, row_count: int = 1) -> pygame.Rect:
    height = _panel_height(row_count)
    shadow_rect = pygame.Rect(
        theme.PANEL_X + theme.SHADOW_OFFSET,
        theme.PANEL_Y + theme.SHADOW_OFFSET,
        theme.PANEL_WIDTH,
        height,
    )
    surface.fill(_BLACK, shadow_rect)

    panel_rect = pygame.Rect(theme.PANEL_X, theme.PANEL_Y, theme.PANEL_WIDTH, height)
    surface.fill(_WHITE, panel_rect)
    pygame.draw.rect(surface, _BLACK, panel_rect, width=1)

    return panel_interior_rect(row_count)


def _item_footprint(center_x: int, top_y: int, item: ItemVisual) -> pygame.Rect:
    """An item's reverse-video footprint rect, in screen coordinates.
    Pure layout math (no drawing) so it can be reused by both draw_item
    and mouse hit-testing without them ever drifting apart."""
    label_size = text_size(item.label, scale=theme.FONT_SCALE)
    status_size = (theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE) if item.status_icon else (0, 0)

    # At least as wide as its content (icon/label/status, plus padding),
    # but never narrower than the column allotted to it by ICON_SPACING,
    # so short labels (e.g. "MEM") still get a properly sized selection
    # box rather than one that hugs just the icon - matching the real
    # Lisa's diagnostic screen, where each item is an evenly sized box.
    content_based_width = max(theme.ICON_SIZE, label_size[0], status_size[0]) + theme.ITEM_CONTENT_PADDING
    content_width = max(content_based_width, theme.ICON_SPACING - theme.ITEM_MIN_WIDTH_SLACK)
    content_height = (
        label_size[1]
        + theme.ITEM_ELEMENT_GAP
        + theme.ICON_SIZE
        + theme.ITEM_ELEMENT_GAP
        + (status_size[1] if item.status_icon else 0)
        + theme.ITEM_CONTENT_PADDING
    )
    footprint = pygame.Rect(0, 0, content_width, content_height)
    footprint.centerx = center_x
    footprint.top = top_y
    return footprint


def item_layout(items: list[ItemVisual]) -> list[pygame.Rect]:
    """Each item's footprint rect, in screen coordinates, in the same
    positions render_frame draws them at - used both for drawing and for
    mouse hit-testing (see hit_test). Items beyond ITEMS_PER_ROW wrap
    onto additional rows, each independently centered, rather than
    overflowing the panel's width."""
    if not items:
        return []
    rows = [items[i : i + theme.ITEMS_PER_ROW] for i in range(0, len(items), theme.ITEMS_PER_ROW)]
    interior = panel_interior_rect(row_count=len(rows))
    spacing = theme.ICON_SPACING

    footprints = []
    row_top = interior.top + theme.ITEMS_TOP_MARGIN
    for row_items in rows:
        total_width = spacing * (len(row_items) - 1)
        start_x = interior.centerx - total_width // 2
        footprints.extend(
            _item_footprint(start_x + index * spacing, row_top, item) for index, item in enumerate(row_items)
        )
        row_top += theme.ITEM_ROW_HEIGHT + theme.ITEMS_ROW_GAP
    return footprints


def hit_test(items: list[ItemVisual], point: tuple[int, int]) -> int | None:
    """Returns the index of the item whose footprint contains `point`
    (screen coordinates), or None if the point isn't over any item -
    used to turn a mouse position into a selection."""
    for index, footprint in enumerate(item_layout(items)):
        if footprint.collidepoint(point):
            return index
    return None


def draw_item(surface: pygame.Surface, center_x: int, top_y: int, item: ItemVisual) -> None:
    footprint = _item_footprint(center_x, top_y, item)
    label_size = text_size(item.label, scale=theme.FONT_SCALE)

    fg_color = _WHITE if item.selected else _BLACK
    bg_color = _BLACK if item.selected else None

    if bg_color is not None:
        surface.fill(bg_color, footprint)

    label_rect = pygame.Rect(0, 0, *label_size)
    label_rect.centerx = center_x
    label_rect.top = footprint.top + theme.ITEM_ELEMENT_GAP
    render_text(surface, item.label, label_rect.left, label_rect.top, scale=theme.FONT_SCALE, color=fg_color)

    icon_rect = pygame.Rect(0, 0, theme.ICON_SIZE, theme.ICON_SIZE)
    icon_rect.centerx = center_x
    icon_rect.top = label_rect.bottom + theme.ITEM_ELEMENT_GAP
    icon_to_draw = item.icon
    if item.selected:
        icon_to_draw = _invert_icon(item.icon)
    surface.blit(icon_to_draw, icon_rect)

    if item.status_icon:
        status_rect = pygame.Rect(0, 0, theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE)
        status_rect.centerx = center_x
        status_rect.top = icon_rect.bottom + theme.ITEM_ELEMENT_GAP
        status_icon_to_draw = item.status_icon
        if item.selected:
            status_icon_to_draw = _invert_icon(item.status_icon)
        surface.blit(status_icon_to_draw, status_rect)


def _invert_icon(icon: pygame.Surface) -> pygame.Surface:
    inverted = icon.copy()
    width, height = inverted.get_size()
    for y in range(height):
        for x in range(width):
            r, g, b, *_ = inverted.get_at((x, y))
            inverted.set_at((x, y), (255 - r, 255 - g, 255 - b))
    return inverted


def draw_top_strip(surface: pygame.Surface) -> None:
    """A thin white bar across the very top of the screen, with a single
    small right-aligned status character - per the spec, a placeholder
    glyph that isn't load-bearing for v1."""
    width, _ = surface.get_size()
    strip_rect = pygame.Rect(0, 0, width, theme.TOP_STRIP_HEIGHT)
    surface.fill(_WHITE, strip_rect)
    char_width, char_height = text_size("H", scale=theme.FONT_SCALE)
    x = width - char_width - theme.PANEL_CONTENT_INSET
    y = (theme.TOP_STRIP_HEIGHT - char_height) // 2
    render_text(surface, "H", x, y, scale=theme.FONT_SCALE, color=_BLACK)


def render_frame(surface: pygame.Surface, line1: str, line2: str, items: list[ItemVisual]) -> None:
    """Draws one full frame directly onto `surface` (the real screen).
    Callers are expected to have already drawn the checkerboard
    (draw_checkerboard_cached) - everything here is opaque and simply
    overdraws it where the top strip/panel/items are."""
    draw_top_strip(surface)
    interior = draw_panel(surface, row_count=_row_count(len(items)))

    render_text(surface, line1, interior.left, interior.top, scale=theme.FONT_SCALE, color=_BLACK)
    if line2:
        render_text(
            surface,
            line2,
            interior.left,
            interior.top + text_size(line1, scale=theme.FONT_SCALE)[1] + theme.HEADER_LINE_GAP,
            scale=theme.FONT_SCALE,
            color=_BLACK,
        )

    for item, footprint in zip(items, item_layout(items)):
        draw_item(surface, footprint.centerx, footprint.top, item)
