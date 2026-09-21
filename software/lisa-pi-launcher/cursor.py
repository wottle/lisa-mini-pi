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
# Also stays well under 64x64: the Pi's vc4/KMS hardware cursor plane
# tops out at 64x64, and a larger cursor surface forces X to fall back to
# a software-rendered cursor, which isn't synced with this app's own
# frame redraws and was causing a visible flicker.
#
# Shrunk (2/3 scale) from an earlier 64/80x64 alongside the icon size
# reduction - it was oversized enough to make the jump into an emulator
# session feel jarring by comparison.
SIZE = 42
_OUTLINE_WIDTH = 3

# Classic arrow-pointer silhouette, tip at the origin (the hotspot).
_ARROW_POINTS = [
    (0, 0),
    (0, 30),
    (7, 23),
    (13, 34),
    (18, 32),
    (13, 21),
    (23, 21),
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
