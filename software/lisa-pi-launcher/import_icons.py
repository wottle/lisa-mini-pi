"""One-time tool: converts the provided high-resolution source icons into
crisp PNGs under icons/ (theme.ICON_SIZE for system and boot-diagnostic
icons, theme.CHECK_ICON_SIZE for the smaller "completed" check badge),
replacing the procedurally-drawn placeholders gen_icons.py made for these
same names. Not part of the runtime path - run directly
(`python3 import_icons.py <source_dir>`) whenever new source art needs
importing.

Two conversion modes (see convert_icon's `threshold` parameter):
- Hard black/white threshold (diag icons, check.png): for source art
  that's already pure black/white line art (no antialiasing/gradients).
  A high-quality downscale followed by a hard threshold keeps that
  purity - avoiding the gray edge pixels a naive resize would leave -
  while cleanly reducing to our target size.
- Smooth grayscale, no threshold (the main system icons as of the
  2026-09-27 icon refresh): for source art with real tonal detail (e.g.
  the classic Mac Finder face's two-tone shading) that a hard threshold
  would destroy - confirmed by a direct side-by-side comparison, not
  guessed. Still monochrome (color source art is composited/grayscaled
  same as before), just not reduced all the way to 1-bit.
"""

import sys

from PIL import Image, ImageOps

import theme

_SOURCE_TO_ICON = {
    "lisa.png": "lisa.png",
    "macos7.png": "macintosh.png",
    "macos6.jpg": "macintosh6.png",
    "next.png": "next.png",
    "appleii.png": "apple2.png",
}

# Boot-diagnostic source art, sized to theme.ICON_SIZE like the icons
# above. check.png is the smaller "completed" status badge and is sized
# separately - see _SOURCE_TO_CHECK_ICON below.
_SOURCE_TO_DIAG_ICON = {
    "CPU.png": "diag_cpu.png",
    "MEM.png": "diag_mem.png",
    "io.png": "diag_io.png",
    "expansion_cards.png": "diag_expansion.png",
}

_CHECK_SOURCE = "check.png"
_CHECK_ICON = "check.png"

_THRESHOLD = 128


def convert_icon(source_path: str, size: int, threshold: bool = True) -> Image.Image:
    image = Image.open(source_path)
    if image.mode in ("RGBA", "LA") or "transparency" in image.info:
        # Composite onto white first: this source's transparent pixels
        # are stored as black (0,0,0,0), which a direct convert("L")
        # would read as black background instead of white, since L
        # conversion drops the alpha channel and just keeps the (wrong)
        # RGB value underneath.
        background = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(background.convert("RGBA"), image.convert("RGBA"))
    image = image.convert("L")
    # Crop to the actual ink's bounding box (plus a little padding) before
    # resizing: the source art isn't drawn at a consistent size relative
    # to its canvas (one icon's content filled ~50% of its canvas width,
    # another's only ~19%), so resizing the full canvas for every icon
    # left some noticeably smaller/thinner than others - thin enough,
    # for the smallest ones, that a stroke could vanish entirely under
    # the hard threshold below.
    # getbbox() treats any non-pure-white pixel as content, but these
    # source images have faint background noise across the whole canvas
    # (not flat 255) - without a stricter threshold here first, the
    # detected bbox is the entire canvas. This threshold is only used to
    # find the crop region; the actual resize below still uses the
    # original (unthresholded) pixel values for a clean LANCZOS downscale.
    bbox_mask = image.point(lambda p: 0 if p < 200 else 255)
    content_bbox = ImageOps.invert(bbox_mask).getbbox()
    if content_bbox is not None:
        left, top, right, bottom = content_bbox
        # A square crop centered on the content, sized to its larger
        # dimension plus padding - not just its own (left, top, right,
        # bottom) box - so content narrower than it is tall (or vice
        # versa) keeps its original aspect ratio instead of being
        # stretched to fill a square target size.
        content_size = max(right - left, bottom - top)
        half_side = content_size // 2 + content_size // 10
        center_x, center_y = (left + right) // 2, (top + bottom) // 2
        image = image.crop((
            max(0, center_x - half_side),
            max(0, center_y - half_side),
            min(image.width, center_x + half_side),
            min(image.height, center_y + half_side),
        ))
    if threshold:
        # NEAREST, not LANCZOS: this source art is already blocky pixel
        # art, not a smooth/photographic image, so a smoothing resample
        # algorithm is the wrong tool - it blends soft gray edges that
        # the hard threshold below then chops at a somewhat arbitrary
        # boundary, producing slightly inconsistent/jagged edges
        # compared to NEAREST (confirmed side by side at both 32px and
        # 48px target sizes).
        image = image.resize((size, size), Image.NEAREST)
        # Hard-threshold back to pure black/white: even NEAREST can land
        # exactly between two source shades at some pixels.
        image = image.point(lambda p: 255 if p >= _THRESHOLD else 0)
        return image.convert("1")
    # LANCZOS here, not NEAREST: this path is for source art with real
    # tonal gradients we want to keep (see the module docstring) - a
    # smoothing resample is the right tool for that, unlike for the
    # blocky pixel-art path above.
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    if len(sys.argv) != 2:
        print("usage: python3 import_icons.py <source_dir>")
        sys.exit(1)
    source_dir = sys.argv[1]

    # Source art for different icon groups often lives in different
    # directories (system icons and boot-diagnostic icons were provided
    # separately) - skip whichever group's files aren't in this
    # particular source_dir rather than aborting the whole run. System
    # icons use threshold=False (smooth grayscale - see module
    # docstring); diag icons stay hard-thresholded 1-bit.
    for source_name, icon_name, threshold in [
        *((name, dest, False) for name, dest in _SOURCE_TO_ICON.items()),
        *((name, dest, True) for name, dest in _SOURCE_TO_DIAG_ICON.items()),
    ]:
        source_path = f"{source_dir}/{source_name}"
        try:
            icon = convert_icon(source_path, theme.ICON_SIZE, threshold=threshold)
        except FileNotFoundError:
            print(f"skipped {icon_name}: {source_path} not found")
            continue
        dest_path = f"icons/{icon_name}"
        icon.save(dest_path)
        print(f"wrote {dest_path} from {source_path}")

    check_source_path = f"{source_dir}/{_CHECK_SOURCE}"
    try:
        check_icon = convert_icon(check_source_path, theme.CHECK_ICON_SIZE)
    except FileNotFoundError:
        print(f"skipped {_CHECK_ICON}: {check_source_path} not found")
    else:
        check_dest_path = f"icons/{_CHECK_ICON}"
        check_icon.save(check_dest_path)
        print(f"wrote {check_dest_path} from {check_source_path}")


if __name__ == "__main__":
    main()
