# 3D Models

STL files for the Lisa Mini Pi case, sized around the repurposed iPad
1/2 LCD panel + controller board (see `../bill-of-materials.md`).

| File | Qty | Notes |
|---|---|---|
| `Lisa-Mini-Pi_Front-iPad-LCD.stl` | 1 | Front panel/bezel, cut for the iPad 1/2 LCD. |
| `Lisa-Mini-Pi_Back-With_Power_Button.stl` | 1 | Back piece **with** a cutout for the keyboard-switch power button + LED. Use this one, not the no-button variant, if you're wiring up the GPIO power button (see `../../docs/software-setup.md` §2). |
| `Lisa-Mini-Pi_Back-NO_Power_Button.stl` | 1 | Back piece with **no** power-button cutout - print this instead if you don't want the extra wiring/parts of a physical power switch. Print exactly one back piece, not both. |
| `Lisa-Mini-Pi_Power-Button.stl` | 1 | The power button cap/bezel itself - only needed with the "With Power Button" back piece. |
| `Lisa-Mini-Pi_LCD-Bottom-Clips_qty2.stl` | **2** | Bottom clips holding the LCD panel in place - print **two** of this part (the `qty2` in the filename is the actual required count, not a typo/leftover). |
| `Lisa-Mini-Pi_LCD-Side-Clips_qty2.stl` | **2** | Side clips holding the LCD panel in place - print **two** of this part as well. |
| `Lisa-Mini-Pi_Lisa-Badge.stl` | 1 | Decorative Lisa logo badge. |
| `Lisa-Mini-Pi_Blank-Small-Badge.stl` | 1 | Blank badge variant, if you'd rather not print the Lisa logo. |
| `Lisa-Mini-Pi_All-Plates.3mf` | - | Slicer project file with every part above laid out on build plates together - open this instead of the individual STLs if your slicer supports `.3mf` and you want everything queued up at once. |

Raspberry Pi mounting fits a Pi 3B, 4B, or 5 - **Pi 4B is the
recommended target**: better performance than a Pi 3B (see
`../bill-of-materials.md`), and unlike a Pi 5, its power needs are
already covered by this case's buck-converter wiring. A Pi 5 boots and
runs the full software stack fine, but this case has no mounting yet for
the dedicated power board a Pi 5 needs for reliable GPIO power delivery -
see the main README's "Project status" for detail.

Assembly instructions (fitting the LCD, wiring the power button, closing
the case) live in `../assembly/README.md`.

## Printing notes

General starting-point settings, carried over from the same builder's
[LisaFPGA case](https://github.com/wottle/lisa-mini/blob/main/docs/PRINTING.md)
(a different, larger case design, but the material and general settings
transfer):

| Setting | Value |
|---|---|
| Wall thickness | ~2.4mm (2 perimeters at 0.4mm nozzle, or adjust to match) |
| Infill | 15–20% |
| Layer height | 0.2mm for most parts; 0.12mm with ironing enabled for `Lisa-Mini-Pi_Lisa-Badge.stl`/`Lisa-Mini-Pi_Blank-Small-Badge.stl` (surface quality on a flat visible logo plate) |
| Material | [Polar Filament Retro Platinum PLA](https://polarfilament.com/products/retro-platinum-pla-1kg-1-75mm) — metallic silver/platinum finish for a classic-computing look; no warping issues on the LisaFPGA case's large front/back shells with this filament |

**Not yet verified for this specific case's parts** (unlike the settings
above, which are safe general-purpose starting points): per-part print
orientation, which parts need supports, and the actual bed size required
- `Lisa-Mini-Pi_All-Plates.3mf` already lays every part out on build
plates, so opening that in your slicer is the fastest way to get real
orientation/plating without guessing. If you print from scratch and
learn anything worth recording here (a part that needs supports, an
orientation that avoided them, the bed size the `.3mf` plates assume),
please contribute it back.
