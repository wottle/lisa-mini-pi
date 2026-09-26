# Bill of Materials

Everything needed to build one Lisa Mini Pi, beyond the 3D-printed parts
in `3d-models/` (see that directory's README for exact STL files/print
quantities).

**Links are convenience references, not endorsements or guaranteed
current** - Amazon/AliExpress listings change/disappear; verify specs
against the notes here before ordering if a link is dead or looks
different than described.

| Part | Qty | Notes | Link |
|---|---|---|---|
| Raspberry Pi | 1 | Pi 4B or Pi 5 recommended (performance - see `../software/lisa-pi-launcher/CLAUDE.md` for why a Pi 3B struggles with Previous/LinApple in particular). Case mounts work at least back to a Pi 3B. | — |
| iPad 1/2 LCD panel + controller board | 1 | "Type 2 with LCD" listing appears to be the correct fit. | [AliExpress](https://www.aliexpress.us/item/3256801532761537.html) |
| 12V→5V buck converter | 1 | Powers the Pi from the same 12V supply as the LCD. | [Amazon](https://a.co/d/07PxophW) |
| 12V 5A power supply | 1 | Powers the buck converter (→ Pi) and the LCD controller board. | — (any reputable 12V/5A barrel-jack supply) |
| 5.5x2.5mm barrel jack | 1 | Connects the 12V supply to the LCD controller board. | [Amazon](https://a.co/d/0buA0dI0) |
| Toggle switch | 1 | Master power switch for the LCD + Pi (cuts 12V before the buck converter/LCD controller, upstream of the GPIO soft-power button below). | [Amazon](https://a.co/d/02DKKr63) |
| Keyboard switch (clear housing recommended, for the light-up GPIO power button) | 1 | Only needed if printing the "With Power Button" back piece - see `3d-models/README.md`. **TODO: link needs fixing** - the one given (`https://a.co/d/07OlQIg0`) is identical to the Dupont wires link below, so it's almost certainly wrong; confirm and replace. | ⚠️ TODO |
| 3mm warm white or yellow LED | 1 | Lights the GPIO power button - see `../docs/software-setup.md` §2 for the GPIO18 wiring. | [Amazon](https://a.co/d/0dTjaJSu) |
| Dupont wires (assorted M/F) | several | For GPIO connections (LED, power-button switch) - see `../docs/software-setup.md` §2 for exact pins. | [Amazon](https://a.co/d/07OlQIg0) |
| 20 AWG wire | a few feet | Power distribution: 12V jack → toggle switch → buck converter, and 12V jack → toggle switch → LCD controller board. | — |
| Resistor, ~1kΩ | 1 | Inline with the power-button switch (3.3V → resistor → switch → GPIO17) - see `../docs/software-setup.md` §2. Not in your list above; flagging since the software docs assume it's there. | — |

## Open items

- Confirm the correct keyboard-switch link (see the TODO row above).
- No specific LED current-limiting resistor was listed either - the
  existing software docs only specify the power-button switch's ~1kΩ
  resistor, not an LED resistor value. Worth adding once you've picked
  one (3mm LEDs are typically fine on a few hundred ohms off a 3.3V
  GPIO, but confirm against the actual LED's forward voltage/current
  rating rather than assuming).
- Quantities above assume one Lisa Mini Pi; scale accordingly for more.
