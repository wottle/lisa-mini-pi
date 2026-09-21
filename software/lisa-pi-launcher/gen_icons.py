"""Procedurally draws small 1-bit ROM-diagnostic-style icons and saves them
as PNGs under icons/. Run directly (`python3 gen_icons.py`) any time an
icon needs regenerating - this is a build-time tool, not part of the
running launcher.

Writes all ten icons, including the eight (lisa/macintosh/next/apple2 and
the four boot-diagnostic icons diag_cpu/mem/io/expansion, plus the
check.png status badge) that import_icons.py can replace with nicer
imported art - run import_icons.py *after* this script if you want those
to take precedence. ibmpc has no imported replacement and is always
sourced from here.
"""

import os

from PIL import Image, ImageDraw

import theme

# Hand-tuned drawing coordinates below assume this native resolution;
# each finished icon is then resized (nearest-neighbor, to stay crisp) to
# theme.ICON_SIZE, the single source of truth every other module uses.
_DRAW_SIZE = 24
ICON_SIZE = theme.ICON_SIZE
_BLACK = 0
_WHITE = 1


def _blank_canvas() -> Image.Image:
    image = Image.new("1", (_DRAW_SIZE, _DRAW_SIZE), _WHITE)
    return image


def draw_macintosh() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Compact-Mac silhouette: rounded body outline with a screen cutout
    # and a small base foot.
    draw.rectangle((4, 2, 19, 17), outline=_BLACK)
    draw.rectangle((7, 5, 16, 12), outline=_BLACK)  # screen
    draw.rectangle((2, 18, 21, 20), outline=_BLACK)  # base
    return image


def draw_lisa() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Boxier/wider than the Mac, with a second slot suggesting the twin
    # floppy/ProFile drives.
    draw.rectangle((2, 3, 21, 16), outline=_BLACK)
    draw.rectangle((4, 5, 12, 11), outline=_BLACK)  # screen
    draw.line((15, 6, 19, 6), fill=_BLACK)  # drive slot 1
    draw.line((15, 9, 19, 9), fill=_BLACK)  # drive slot 2
    draw.rectangle((0, 17, 23, 19), outline=_BLACK)  # base
    return image


def draw_next() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # NeXT was famously a solid black cube.
    draw.rectangle((5, 5, 18, 18), fill=_BLACK)
    return image


def draw_apple2() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Wide low keyboard body with a monitor perched on top, offset back.
    draw.rectangle((2, 14, 21, 20), outline=_BLACK)  # keyboard/body
    draw.rectangle((6, 3, 17, 13), outline=_BLACK)  # monitor
    draw.rectangle((8, 5, 15, 10), outline=_BLACK)  # screen
    return image


def draw_ibmpc() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Separate rectangular system unit next to/under a monitor.
    draw.rectangle((2, 8, 10, 20), outline=_BLACK)  # system unit
    draw.rectangle((12, 3, 22, 15), outline=_BLACK)  # monitor
    draw.rectangle((14, 5, 20, 11), outline=_BLACK)  # screen
    return image


def draw_diag_cpu() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A chip: a square body with small pin ticks on each side.
    draw.rectangle((6, 6, 17, 17), outline=_BLACK)
    for x in (8, 11, 14, 17):
        draw.line((x, 3, x, 6), fill=_BLACK)
        draw.line((x, 17, x, 20), fill=_BLACK)
    return image


def draw_diag_mem() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A simple memory-module outline: a rectangle with notch marks.
    draw.rectangle((3, 8, 20, 15), outline=_BLACK)
    for x in range(5, 20, 3):
        draw.line((x, 8, x, 10), fill=_BLACK)
    return image


def draw_diag_io() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A small waveform/squiggle suggesting serial I/O activity.
    points = [(3, 12), (7, 6), (11, 18), (15, 6), (19, 18), (21, 12)]
    draw.line(points, fill=_BLACK)
    return image


def draw_diag_expansion() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A blank expansion-card silhouette: a card body with edge-connector
    # teeth along the bottom, matching the CPU/MEM/I-O card style.
    draw.rectangle((5, 3, 18, 17), outline=_BLACK)
    for x in range(6, 18, 2):
        draw.line((x, 17, x, 20), fill=_BLACK)
    return image


def draw_check() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A simple checkmark, thickened by drawing it twice offset by one
    # pixel (PIL's line drawing has no width>1 support for polylines).
    for dx in (0, 1):
        draw.line([(3 + dx, 12), (9, 18), (20, 4)], fill=_BLACK, width=2)
    return image


_ICONS = {
    "macintosh.png": draw_macintosh,
    "lisa.png": draw_lisa,
    "next.png": draw_next,
    "apple2.png": draw_apple2,
    "ibmpc.png": draw_ibmpc,
    "diag_cpu.png": draw_diag_cpu,
    "diag_mem.png": draw_diag_mem,
    "diag_io.png": draw_diag_io,
    "diag_expansion.png": draw_diag_expansion,
}


def main() -> None:
    os.makedirs("icons", exist_ok=True)
    for filename, drawer in _ICONS.items():
        image = drawer()
        if ICON_SIZE != _DRAW_SIZE:
            image = image.resize((ICON_SIZE, ICON_SIZE), Image.NEAREST)
        image.save(os.path.join("icons", filename))
        print(f"wrote icons/{filename}")

    check_image = draw_check()
    if theme.CHECK_ICON_SIZE != _DRAW_SIZE:
        check_image = check_image.resize((theme.CHECK_ICON_SIZE, theme.CHECK_ICON_SIZE), Image.NEAREST)
    check_image.save(os.path.join("icons", "check.png"))
    print("wrote icons/check.png")


if __name__ == "__main__":
    main()
