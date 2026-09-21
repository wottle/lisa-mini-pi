"""A big, chunky monochrome mouse pointer, styled to match the project's
1-bit aesthetic - for someone starting the Pi without a keyboard attached,
who needs to be able to see and use the pointer to pick a system."""

import pygame

_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)
_TRANSPARENT_KEY = (1, 2, 3)

# Real screen pixels - like the checkerboard, this is drawn directly at
# native resolution (SDL cursors aren't run through our own logical-
# surface scaling pipeline at all), so a real-pixel size is what actually
# controls how big it looks.
#
# Capped at 64x64 (down from an earlier 80x80): the Pi's vc4/KMS hardware
# cursor plane tops out at 64x64. A larger cursor surface forces X to fall
# back to a software-rendered cursor, which isn't synced with this app's
# own frame redraws and was causing a visible flicker.
SIZE = 64
_OUTLINE_WIDTH = 5

# Classic arrow-pointer silhouette, tip at the origin (the hotspot).
_ARROW_POINTS = [
    (0, 0),
    (0, 45),
    (11, 35),
    (19, 51),
    (27, 48),
    (19, 32),
    (34, 32),
]


def build_cursor_surface() -> pygame.Surface:
    surface = pygame.Surface((SIZE, SIZE))
    surface.fill(_TRANSPARENT_KEY)
    surface.set_colorkey(_TRANSPARENT_KEY)
    pygame.draw.polygon(surface, _WHITE, _ARROW_POINTS)
    pygame.draw.polygon(surface, _BLACK, _ARROW_POINTS, width=_OUTLINE_WIDTH)
    return surface


def set_cursor() -> None:
    surface = build_cursor_surface()
    pygame.mouse.set_cursor(pygame.cursors.Cursor((0, 0), surface))
