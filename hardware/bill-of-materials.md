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
| Raspberry Pi | 1 | **Pi 4B recommended.** A Pi 3B works but struggles with Previous/LinApple in particular (see `../software/lisa-pi-launcher/CLAUDE.md`); a Pi 5 runs everything fine but this case's power wiring (below) doesn't yet reliably support one - see the main README's "Project status". Case mounts fit all three. | — |
| microSD card, 32GB | 1 | Real measured usage on a fully-loaded Pi 4 (all five emulators, all disk images): 13GB used of a 29GB card (2026-09-26) - 32GB gives comfortable headroom; go 64GB if you want more margin for future growth (e.g. larger assets if the project moves to a higher-res LCD panel) or just don't want to think about it again. 16GB would be uncomfortably tight. | — |
| iPad 1/2 LCD panel + controller board | 1 | "Type 2 with LCD" listing appears to be the correct fit. | [AliExpress](https://www.aliexpress.us/item/3256801532761537.html) |
| 12V→5V buck converter | 1 | Powers the Pi from the same 12V supply as the LCD. **Adjustable output** - ships set to an arbitrary voltage; must be calibrated to ~5.1V with a multimeter before ever connecting it to the Pi's GPIO pins, every time, even on a converter you've calibrated before. See `assembly/README.md` §5. | [Amazon](https://a.co/d/07PxophW) |
| 12V 5A power supply | 1 | Powers the buck converter (→ Pi) and the LCD controller board. | — (any reputable 12V/5A barrel-jack supply) |
| 5.5x2.5mm barrel jack (panel-mount, female) | 1 | The case's main power *input* - mounts through the hole in the back piece (secured with its own washer/nut), feeding the rocker switch. See `assembly/README.md` §2. | [Amazon](https://a.co/d/0buA0dI0) |
| 5.5x2.5mm barrel jack (pigtail, male) | 1 | A second one, wired to a short pigtail, to connect the rocker switch's output to the LCD controller board's own 12V barrel-jack input (if your controller board takes power that way - see `assembly/README.md` §3). Confirmed correct listing (2026-09-27) - a different part than the panel-mount jack above. | [Amazon](https://a.co/d/0fmf5a9l) |
| Rocker switch | 1 | Master power switch for the LCD + Pi (cuts 12V before the buck converter/LCD controller, upstream of the GPIO soft-power button below) - see `assembly/README.md` §2. | [Amazon](https://a.co/d/02DKKr63) |
| Keyboard switch (clear housing recommended, for the light-up GPIO power button) | 1 | Only needed if printing the "With Power Button" back piece - see `3d-models/README.md`. Confirmed correct listing (2026-09-27) - was out of stock as of this writing, so it may need a substitute if still unavailable. | [Amazon](https://a.co/d/05LYYxer) |
| 3mm warm white or yellow LED | 1 | Lights the GPIO power button - see `../docs/software-setup.md` §2 for the GPIO18 wiring. | [Amazon](https://a.co/d/0dTjaJSu) |
| Dupont wires (assorted M/F) | several | For GPIO connections (LED, power-button switch) - see `../docs/software-setup.md` §2 for exact pins. | [Amazon](https://a.co/d/07OlQIg0) |
| 20 AWG wire | a few feet | Power distribution: 12V jack → toggle switch → buck converter, and 12V jack → toggle switch → LCD controller board. | — |
| Resistor, 330Ω | 2 | One inline with the power-button switch (3.3V → resistor → switch → GPIO17), one inline with the LED (GPIO18 → resistor → LED → GND) - both confirmed on real hardware (2026-09-27). See `../docs/software-setup.md` §2. | — |
| Heat-shrink tubing, assorted | a few feet | Insulates every soldered connection in the power/switch/LED wiring before it's routed into the case - see `assembly/README.md` §4. | — |
| M3×4mm screws | 8 | Mounts the LCD's side clip (1), bottom clips (2), and the controller board(s) (2 each - 4 if there's an optional button board too) - see `assembly/README.md` §6-7. | — |
| 1.5mm pointed screws (small) | 4 | Mounts the Pi board to the back piece. **Go easy on these** - the printed screw mounts are delicate and have cracked on at least one build; hot glue is a working fallback if a mount breaks. See `assembly/README.md` §1. | — |
| Kapton tape | small roll | Optional - useful for pinning down an auxiliary/button board's wiring if it has no mounting holes of its own. | — |
| Multimeter | 1 | Required to calibrate the buck converter's output voltage before connecting it to the Pi - see the buck converter row above and `assembly/README.md` §5. Not consumed by the build; any basic multimeter works. | — |

## Open items

- Quantities above assume one Lisa Mini Pi; scale accordingly for more.
