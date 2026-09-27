"""Composes the checkerboard background and the "CHOOSE YOUR ADVENTURE"
panel (title, rule, a row of bordered item cards, a second rule, and a
footer hint row) directly onto the real screen surface - see theme.py
for why there's no separate logical/design surface scaled up to it."""

from dataclasses import dataclass

import pygame

import theme
from bitmap_font import render_text, text_size

_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)

_FOOTER_LEFT = "< > SELECT"
_FOOTER_CENTER = "RETURN OR CLICK TO START"
_FOOTER_SHUTDOWN = "S SHUT DOWN"
_FOOTER_QUIT = "Q QUIT"

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
    subtitle: str = ""


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
    height = _panel_height(row_count)
    return pygame.Rect(
        theme.PANEL_X + theme.PANEL_CONTENT_INSET,
        theme.PANEL_Y + theme.PANEL_CONTENT_INSET,
        theme.PANEL_WIDTH - 2 * theme.PANEL_CONTENT_INSET,
        height - 2 * theme.PANEL_CONTENT_INSET,
    )


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


def _grid_top(interior: pygame.Rect) -> int:
    """Y coordinate (screen space) of the top of the item-card grid, i.e.
    just below the title and its rule. Shared by item_layout() (used for
    mouse hit-testing) and render_frame() (used for actually drawing) so
    they can never drift apart - the title's height only depends on
    FONT_SCALE, never on the header text's actual content/length, so this
    needs no header-text argument."""
    title_height = text_size("X", scale=theme.FONT_SCALE)[1]
    return interior.top + title_height + theme.HEADER_RULE_GAP + theme.RULE_THICKNESS + theme.RULE_TO_GRID_GAP


def _item_box_rect(center_x: int, top_y: int) -> pygame.Rect:
    """A single item card's rect, in screen coordinates. Pure layout math
    (no drawing) so it can be reused by both draw_item and mouse
    hit-testing without them ever drifting apart."""
    rect = pygame.Rect(0, 0, theme.ITEM_BOX_WIDTH, theme.ITEM_ROW_HEIGHT)
    rect.centerx = center_x
    rect.top = top_y
    return rect


def item_layout(items: list[ItemVisual]) -> list[pygame.Rect]:
    """Each item card's rect, in screen coordinates, in the same
    positions render_frame actually draws them at - used both for
    drawing and for mouse hit-testing (see hit_test). Items beyond
    ITEMS_PER_ROW wrap onto additional rows, each independently
    centered, rather than overflowing the panel's width."""
    if not items:
        return []
    rows = [items[i : i + theme.ITEMS_PER_ROW] for i in range(0, len(items), theme.ITEMS_PER_ROW)]
    interior = panel_interior_rect(row_count=len(rows))
    spacing = theme.ICON_SPACING

    rects = []
    row_top = _grid_top(interior)
    for row_items in rows:
        total_width = spacing * (len(row_items) - 1)
        start_x = interior.centerx - total_width // 2
        rects.extend(
            _item_box_rect(start_x + index * spacing, row_top) for index, _ in enumerate(row_items)
        )
        row_top += theme.ITEM_ROW_HEIGHT + theme.ITEMS_ROW_GAP
    return rects


def hit_test(items: list[ItemVisual], point: tuple[int, int]) -> int | None:
    """Returns the index of the item whose card contains `point` (screen
    coordinates), or None if the point isn't over any item - used to
    turn a mouse position into a selection."""
    for index, rect in enumerate(item_layout(items)):
        if rect.collidepoint(point):
            return index
    return None


def _footer_y(interior: pygame.Rect, row_count: int) -> int:
    """Y coordinate (screen space) of the footer text row - the same
    formula render_frame uses to actually draw it, factored out so
    footer_layout() (hit-testing/hover) can never drift from it."""
    grid_bottom = _grid_top(interior) + row_count * theme.ITEM_ROW_HEIGHT + max(0, row_count - 1) * theme.ITEMS_ROW_GAP
    second_rule_y = grid_bottom + theme.GRID_TO_RULE_GAP
    return second_rule_y + theme.RULE_THICKNESS + theme.RULE_TO_FOOTER_GAP


def _footer_button_rect(label: str, right_x: int, top_y: int) -> pygame.Rect:
    """A footer button's rect (SHUT DOWN or QUIT), in screen coordinates,
    padded around its text (FOOTER_BUTTON_PADDING) so the hover/click
    target is bigger than the glyphs themselves - the padding is
    symmetric, so the *text* still ends up right-edge-anchored at
    `right_x` and top-anchored at `top_y`, exactly where an unpadded
    label would have gone. Pure layout math, shared by drawing and
    hit-testing (see footer_layout)."""
    pad = theme.FOOTER_BUTTON_PADDING
    size = text_size(label, scale=theme.FONT_SCALE)
    rect = pygame.Rect(0, 0, size[0] + 2 * pad, size[1] + 2 * pad)
    rect.right = right_x + pad
    rect.top = top_y - pad
    return rect


def footer_layout(items: list[ItemVisual]) -> dict[str, pygame.Rect]:
    """SHUT DOWN/QUIT button rects, in screen coordinates, in the same
    positions render_frame actually draws them at - used both for
    drawing (hover highlight) and for mouse hit-testing (see
    footer_hit_test)."""
    row_count = _row_count(len(items))
    interior = panel_interior_rect(row_count=row_count)
    footer_y = _footer_y(interior, row_count)
    quit_rect = _footer_button_rect(_FOOTER_QUIT, interior.right, footer_y)
    shutdown_rect = _footer_button_rect(_FOOTER_SHUTDOWN, quit_rect.left - theme.FOOTER_BUTTON_GAP, footer_y)
    return {"shutdown": shutdown_rect, "quit": quit_rect}


def footer_hit_test(items: list[ItemVisual], point: tuple[int, int]) -> str | None:
    """Returns "shutdown", "quit", or None - used to turn a mouse
    position into a footer button action, mirroring hit_test() for the
    system grid."""
    for name, rect in footer_layout(items).items():
        if rect.collidepoint(point):
            return name
    return None


_CONFIRMATION_MESSAGES = {
    "shutdown": "SHUT DOWN THE PI?",
    "quit": "QUIT TO DESKTOP?",
}


def confirmation_message(action: str) -> str:
    return _CONFIRMATION_MESSAGES[action]


def _confirm_dialog_rect() -> pygame.Rect:
    rect = pygame.Rect(0, 0, theme.CONFIRM_DIALOG_WIDTH, theme.CONFIRM_DIALOG_HEIGHT)
    rect.center = (theme.SCREEN_WIDTH // 2, theme.SCREEN_HEIGHT // 2)
    return rect


def _confirm_button_rect(label: str, center_x: int, center_y: int) -> pygame.Rect:
    """A CONFIRM/CANCEL button's rect, in screen coordinates, padded
    around its text so the click/hover target is bigger than the glyphs
    themselves. Pure layout math, shared by drawing and hit-testing (see
    confirmation_button_layout)."""
    size = text_size(label, scale=theme.FONT_SCALE)
    rect = pygame.Rect(0, 0, size[0] + 2 * theme.CONFIRM_BUTTON_PADDING, size[1] + 2 * theme.CONFIRM_BUTTON_PADDING)
    rect.center = (center_x, center_y)
    return rect


def confirmation_button_layout() -> dict[str, pygame.Rect]:
    """CONFIRM/CANCEL button rects, in screen coordinates, in the same
    positions draw_confirmation_dialog actually draws them at - used both
    for drawing (hover highlight) and for mouse hit-testing (see
    confirmation_hit_test)."""
    dialog = _confirm_dialog_rect()
    button_y = dialog.bottom - theme.CONFIRM_DIALOG_BUTTONS_BOTTOM_GAP
    confirm_width = text_size("CONFIRM", scale=theme.FONT_SCALE)[0] + 2 * theme.CONFIRM_BUTTON_PADDING
    cancel_width = text_size("CANCEL", scale=theme.FONT_SCALE)[0] + 2 * theme.CONFIRM_BUTTON_PADDING
    total_width = confirm_width + theme.CONFIRM_BUTTON_GAP + cancel_width
    confirm_center_x = dialog.centerx - total_width // 2 + confirm_width // 2
    cancel_center_x = confirm_center_x + confirm_width // 2 + theme.CONFIRM_BUTTON_GAP + cancel_width // 2
    return {
        "confirm": _confirm_button_rect("CONFIRM", confirm_center_x, button_y),
        "cancel": _confirm_button_rect("CANCEL", cancel_center_x, button_y),
    }


def confirmation_hit_test(point: tuple[int, int]) -> str | None:
    """Returns "confirm", "cancel", or None - used to turn a mouse
    position into a confirmation-dialog action."""
    for name, rect in confirmation_button_layout().items():
        if rect.collidepoint(point):
            return name
    return None


def draw_confirmation_dialog(surface: pygame.Surface, action: str, hovered: str | None = None) -> None:
    """Draws the SHUT DOWN/QUIT confirmation dialog directly onto
    `surface`, replacing the normal picker frame while
    Phase.CONFIRMING - see launcher.py's main loop."""
    dialog = _confirm_dialog_rect()
    shadow_rect = dialog.move(theme.SHADOW_OFFSET, theme.SHADOW_OFFSET)
    surface.fill(_BLACK, shadow_rect)
    surface.fill(_WHITE, dialog)
    pygame.draw.rect(surface, _BLACK, dialog, width=1)

    message = confirmation_message(action)
    message_size = text_size(message, scale=theme.FONT_SCALE)
    message_rect = pygame.Rect(0, 0, *message_size)
    message_rect.centerx = dialog.centerx
    message_rect.top = dialog.top + theme.CONFIRM_DIALOG_MESSAGE_TOP_GAP
    render_text(surface, message, message_rect.left, message_rect.top, scale=theme.FONT_SCALE, color=_BLACK)

    buttons = confirmation_button_layout()
    for name, label in (("confirm", "CONFIRM"), ("cancel", "CANCEL")):
        rect = buttons[name]
        is_hot = hovered == name
        fg = _WHITE if is_hot else _BLACK
        if is_hot:
            surface.fill(_BLACK, rect)
        pygame.draw.rect(surface, _BLACK, rect, width=1)
        label_size = text_size(label, scale=theme.FONT_SCALE)
        label_rect = pygame.Rect(0, 0, *label_size)
        label_rect.center = rect.center
        render_text(surface, label, label_rect.left, label_rect.top, scale=theme.FONT_SCALE, color=fg)


def draw_item(surface: pygame.Surface, center_x: int, top_y: int, item: ItemVisual) -> None:
    rect = _item_box_rect(center_x, top_y)

    fg_color = _WHITE if item.selected else _BLACK
    bg_color = _BLACK if item.selected else _WHITE

    surface.fill(bg_color, rect)
    pygame.draw.rect(surface, _BLACK, rect, width=1)

    icon_rect = pygame.Rect(0, 0, theme.ICON_SIZE, theme.ICON_SIZE)
    icon_rect.centerx = center_x
    icon_rect.top = rect.top + theme.ITEM_BOX_PADDING_TOP
    icon_to_draw = item.icon
    if item.selected:
        icon_to_draw = _invert_icon(item.icon)
    surface.blit(icon_to_draw, icon_rect)

    label_size = text_size(item.label, scale=theme.FONT_SCALE)
    label_rect = pygame.Rect(0, 0, *label_size)
    label_rect.centerx = center_x
    label_rect.top = icon_rect.bottom + theme.ITEM_BOX_ICON_NAME_GAP
    render_text(surface, item.label, label_rect.left, label_rect.top, scale=theme.FONT_SCALE, color=fg_color)

    if item.subtitle:
        subtitle_size = text_size(item.subtitle, scale=theme.SUBTITLE_FONT_SCALE)
        subtitle_rect = pygame.Rect(0, 0, *subtitle_size)
        subtitle_rect.centerx = center_x
        subtitle_rect.top = label_rect.bottom + theme.ITEM_BOX_NAME_SUBTITLE_GAP
        render_text(
            surface, item.subtitle, subtitle_rect.left, subtitle_rect.top,
            scale=theme.SUBTITLE_FONT_SCALE, color=fg_color,
        )

    if item.status_icon:
        status_rect = pygame.Rect(0, 0, theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE)
        status_rect.centerx = center_x
        status_rect.top = label_rect.bottom + theme.ITEM_BOX_NAME_SUBTITLE_GAP
        status_icon_to_draw = item.status_icon
        if item.selected:
            status_icon_to_draw = _invert_icon(item.status_icon)
        surface.blit(status_icon_to_draw, status_rect)


# Keyed by id(icon): icon surfaces are loaded once at startup and never
# mutated, so each one's inverted counterpart only ever needs computing
# once rather than on every frame it's selected.
_inverted_icon_cache: dict[int, pygame.Surface] = {}


def _invert_icon(icon: pygame.Surface) -> pygame.Surface:
    cached = _inverted_icon_cache.get(id(icon))
    if cached is not None:
        return cached
    # A per-pixel get_at/set_at loop here was the actual cause of the
    # picker feeling sluggish once icons grew to 128px (16384 pixels,
    # decoded/re-encoded one at a time in interpreted Python, every frame
    # the item was selected). BLEND_RGB_SUB does the same 255-minus-value
    # inversion as a single hardware-accelerated blit instead.
    inverted = pygame.Surface(icon.get_size())
    inverted.fill(_WHITE)
    inverted.blit(icon, (0, 0), special_flags=pygame.BLEND_RGB_SUB)
    _inverted_icon_cache[id(icon)] = inverted
    return inverted


def _draw_rule(surface: pygame.Surface, interior: pygame.Rect, y: int) -> None:
    surface.fill(_BLACK, pygame.Rect(interior.left, y, interior.width, theme.RULE_THICKNESS))


def render_frame(
    surface: pygame.Surface,
    header_text: str,
    items: list[ItemVisual],
    hovered_footer: str | None = None,
) -> None:
    """Draws one full frame directly onto `surface` (the real screen).
    Callers are expected to have already drawn the checkerboard
    (draw_checkerboard_cached) - everything here is opaque and simply
    overdraws it where the panel is."""
    row_count = _row_count(len(items))
    interior = draw_panel(surface, row_count=row_count)

    render_text(surface, header_text, interior.left, interior.top, scale=theme.FONT_SCALE, color=_BLACK)

    title_bottom = interior.top + text_size("X", scale=theme.FONT_SCALE)[1]
    first_rule_y = title_bottom + theme.HEADER_RULE_GAP
    _draw_rule(surface, interior, first_rule_y)

    item_rects = item_layout(items)
    for item, rect in zip(items, item_rects):
        draw_item(surface, rect.centerx, rect.top, item)

    grid_bottom = _grid_top(interior) + row_count * theme.ITEM_ROW_HEIGHT + max(0, row_count - 1) * theme.ITEMS_ROW_GAP
    second_rule_y = grid_bottom + theme.GRID_TO_RULE_GAP
    _draw_rule(surface, interior, second_rule_y)

    footer_y = second_rule_y + theme.RULE_THICKNESS + theme.RULE_TO_FOOTER_GAP
    render_text(surface, _FOOTER_LEFT, interior.left, footer_y, scale=theme.FONT_SCALE, color=_BLACK)
    center_size = text_size(_FOOTER_CENTER, scale=theme.FONT_SCALE)
    render_text(
        surface, _FOOTER_CENTER, interior.centerx - center_size[0] // 2, footer_y,
        scale=theme.FONT_SCALE, color=_BLACK,
    )

    footer_buttons = footer_layout(items)
    pad = theme.FOOTER_BUTTON_PADDING
    for name, label in (("shutdown", _FOOTER_SHUTDOWN), ("quit", _FOOTER_QUIT)):
        rect = footer_buttons[name]
        is_hot = hovered_footer == name
        fg = _WHITE if is_hot else _BLACK
        if is_hot:
            surface.fill(_BLACK, rect)
        render_text(surface, label, rect.left + pad, rect.top + pad, scale=theme.FONT_SCALE, color=fg)
