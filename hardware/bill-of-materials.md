# Bill of Materials

Everything needed to build one Lisa Mini Pi, beyond the 3D-printed parts
in `3d-models/` (see that directory's README for exact STL files/print
quantities).

**Links are convenience references, not endorsements or guaranteed
current** - Amazon/AliExpress listings change/disappear; verify specs
against the notes here before ordering if a link is dead or looks
different than described.

Full wiring diagram (buck converter power, switch, LED, exact pins):
`pi-wiring-diagram.svg`.

| Part | Qty | Notes | Link |
|---|---|---|---|
| Raspberry Pi | 1 | Pi 4B or Pi 5 recommended (performance - see `../software/lisa-pi-launcher/CLAUDE.md` for why a Pi 3B struggles with Previous/LinApple in particular). Case mounts work at least back to a Pi 3B. | — |
| microSD card, 32GB | 1 | Real measured usage on a fully-loaded Pi 4 (all five emulators, all disk images): 13GB used of a 29GB card (2026-09-26) - 32GB gives comfortable headroom; go 64GB if you want more margin for future growth (e.g. larger assets if the project moves to a higher-res LCD panel) or just don't want to think about it again. 16GB would be uncomfortably tight. | — |
| iPad 1/2 LCD panel + controller board | 1 | "Type 2 with LCD" listing appears to be the correct fit. | [AliExpress](https://www.aliexpress.us/item/3256801532761537.html) |
| 12V→5V buck converter | 1 | Powers the Pi from the same 12V supply as the LCD. | [Amazon](https://a.co/d/07PxophW) |
| 12V 5A power supply | 1 | Powers the buck converter (→ Pi) and the LCD controller board. | — (any reputable 12V/5A barrel-jack supply) |
| 5.5x2.5mm barrel jack | 1 | Connects the 12V supply to the LCD controller board. | [Amazon](https://a.co/d/0buA0dI0) |
| Toggle switch | 1 | Master power switch for the LCD + Pi (cuts 12V before the buck converter/LCD controller, upstream of the GPIO soft-power button below). | [Amazon](https://a.co/d/02DKKr63) |
| Keyboard switch (clear housing recommended, for the light-up GPIO power button) | 1 | Only needed if printing the "With Power Button" back piece - see `3d-models/README.md`. Confirmed correct listing (2026-09-27) - was out of stock as of this writing, so it may need a substitute if still unavailable. | [Amazon](https://a.co/d/05LYYxer) |
| 3mm warm white or yellow LED | 1 | Lights the GPIO power button - see `../docs/software-setup.md` §2 for the GPIO18 wiring. | [Amazon](https://a.co/d/0dTjaJSu) |
| Dupont wires (assorted M/F) | several | For GPIO connections (LED, power-button switch) - see `../docs/software-setup.md` §2 for exact pins. | [Amazon](https://a.co/d/07OlQIg0) |
| 20 AWG wire | a few feet | Power distribution: 12V jack → toggle switch → buck converter, and 12V jack → toggle switch → LCD controller board. | — |
| Resistor, 330Ω | 2 | One inline with the power-button switch (3.3V → resistor → switch → GPIO17), one inline with the LED (GPIO18 → resistor → LED → GND) - both confirmed on real hardware (2026-09-27). See `../docs/software-setup.md` §2. | — |

## Open items

- Quantities above assume one Lisa Mini Pi; scale accordingly for more.
