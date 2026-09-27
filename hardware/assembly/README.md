# Assembly Instructions

Step-by-step build for the iPad 1/2 LCD + external buck-converter power
variant documented elsewhere in this repo (see `../3d-models/README.md`
for STL files/quantities, `../bill-of-materials.md` for parts, and
`../pi-wiring-diagram.svg` for the exact GPIO/power pinout referenced
throughout). Confirmed on a real build, with photos throughout,
2026-09-27.

## 1. Back piece: mount the Pi

Screw the Pi board down using 4 small 1.5mm pointed screws, one at each
corner mounting hole.

**Be careful when driving these screws — the printed screw mounts are
small and delicate.** All four cracked on one build despite not cracking
on earlier prints of the same model; the Pi was secured with hot glue as
a fallback in that case. Consider reinforcing/thickening these mounts in
the model, or just go slow and stop at the first sign of resistance
rather than forcing it.

## 2. Back piece: power jack and rocker switch

1. Insert the DC barrel jack through its hole in the back of the case,
   and secure it from inside with the washer and nut it comes with.
2. Pop the rocker switch into the larger hole in the back piece (press
   fit).
3. Wire the rocker switch so it's the master cutoff for both the LCD and
   the Pi (via the buck converter):
   - Solder the barrel jack's **positive (red)** wire to one blade on
     the back of the rocker switch.
   - The barrel jack's **negative (black)** wire splits to two black
     wires — one eventually goes to the buck converter's input, the
     other to the LCD controller board's power input.
   - Both **red** power wires (the ones heading to the buck converter
     and the LCD controller) get soldered together to the rocker
     switch's **other** blade.
   - Net result: flipping the rocker switch cuts power to the LCD and to
     the Pi (through the buck converter) at the same time.

![Rocker switch terminals, wires soldered on and heat-shrunk](images/rocker_switch_pins_closeup.jpg)

![Barrel jack and rocker switch installed, seen from outside the back piece](images/underside_of_port_cutout_with_pi_ports_and_dc_jack.jpg)

## 3. Back piece: buck converter and LCD controller power

1. Screw the buck converter down onto one of the two sets of standoffs
   on the inside of the back piece.
2. Solder one of the black/red wire pairs from step 2 to the buck
   converter's input (negative/positive respectively).
3. For the LCD controller board's power input: if yours takes 12V via a
   barrel jack (as this build's does), terminate the other black/red
   wire pair in a barrel-jack plug and connect that to the controller
   board.

![Buck converter mounted on its standoffs, input/output wires soldered on](images/buck_converter.jpg)

![Back piece with Pi, buck converter, and switch/LED wiring all in place](images/Back_everything_secured_and_connected.jpg)

## 4. Back piece: power-button switch and LED

Wire the keyboard-switch power button and its LED per
`../pi-wiring-diagram.svg`:

1. Solder a Dupont wire to each of the two legs on the back of the
   keyboard switch, and a Dupont wire to each of the LED's two legs (4
   wires total).
2. Add an inline 330Ω resistor on **one** of the switch's two wires, and
   on the LED's **positive** leg wire — matching R1/R2 in the wiring
   diagram.
3. Heat-shrink every connection so nothing can short once it's routed
   into the case.
4. Mount the LED: most keyboard switches have a slot the LED's legs can
   run through. Route them through it, then secure the LED close to the
   switch's base with a dab of hot glue — this keeps it from touching or
   rubbing the switch's keycap when pressed. LED orientation (legs toward
   the top or bottom of the switch) doesn't matter functionally; this
   build used bottom.
5. Feed all 4 wires off the bottom of the switch through the hole in the
   front of the back piece (the one that opens into the case interior).
   It's easier one wire at a time — start with the two that have inline
   resistors, since they're the least flexible to maneuver.
6. Push the keyboard switch's keycap down into its slot — it should
   click lightly into place.
7. Plug the 4 Dupont wires into the GPIO pins shown in the wiring
   diagram (GPIO17/3.3V for the switch, GPIO18/GND for the LED).

![Switch keycap seated in its slot, LED visible beside it](images/key_switch_LED_closeup.jpg)

![Switch/LED wires routed through the case wall into the interior](images/key_switch_with_LED.jpg)

## 5. Back piece: Pi power and video

1. **Before connecting anything to the Pi**, calibrate the buck
   converter's output: with the barrel jack's power connected and the
   rocker switch on, put a multimeter on the buck converter's output
   terminals and adjust its trim screw until it reads roughly **5.1V**.
   These converters ship set to an arbitrary voltage, not necessarily
   safe for the Pi - do this check every time, even if you've calibrated
   one before, and definitely before the next step ever touches the Pi's
   GPIO pins.
2. Run two more Dupont wires from the buck converter's output to the
   Pi's GPIO **Pin 2** (5V) and **Pin 6** (GND) — see the wiring diagram.
   This is how the Pi gets power in this build, not through its
   USB-C/micro-USB port — **never connect USB power at the same time**.
3. Plug a micro-HDMI-to-HDMI cable into the Pi.

![Switch/LED and buck-converter-power wires plugged into the Pi's GPIO header](images/PI_GPIO_pins.jpg)

The back piece is now complete.

![Back piece fully assembled, seen from outside](images/back_fully_assembled.jpg)

## 6. Front piece: mount the LCD panel

1. Check the LCD panel's edges first: many iPad LCD panels have small
   metal screw-down tabs sticking out on three sides (visible in the
   corner shot below). These may not sit flush enough for the panel to
   fit the case as printed - if not, bend the tabs flat against the
   panel's edge, or trim them off with wire snips (watch for sharp edges
   if you cut). Better to find this out now than after step 3's clip is
   already screwed down.
2. One corner of the front piece's 3D print has a notch sized for the
   LCD panel's corner. Start there: slide that corner in and push the
   panel all the way toward the case's thin edge.

   ![LCD panel's corner sliding into the front piece's notch - note the metal screw-down tab visible on this edge](images/LCD_corner_slide_into_slot_first.jpg)

3. Take a 3D-printed **side clip**, slide it over its standoff screw
   hole and over the LCD panel's edge, push it snug, then secure it with
   an M3×4mm screw.

   ![Side clip screwed down over the LCD panel's edge](images/LCD_side_clip.jpg)

4. Take the two 3D-printed **bottom clips** and screw each into its
   mounting block on the bottom of the case with an M3×4mm screw. The
   LCD panel should now be fully secured to the front piece.

   ![Bottom clip #1 screwed into place](images/LCD_bottom_clip1.jpg)
   ![Bottom clip #2 screwed into place](images/LCD_bottom_clip2.jpg)

## 7. Front piece: mount the controller board(s)

1. Secure the LCD controller board (and the optional button board, if
   your panel kit has one) to the inside of the front piece, 2×
   M3×4mm screws each.
2. Tuck all wiring as flush against the front piece as you can — it has
   to close against the back piece later. Kapton tape works well for
   pinning down an auxiliary board's wiring if it doesn't have its own
   mounting holes.

![LCD controller board secured, ribbon cable connected](images/LCD_controller_board_secured.jpg)

![Optional button board (SOURCE/MENU/POWER) secured](images/LCD_button_board_secured.jpg)

![Front piece with LCD, controller board, and button board all secured](images/front_panel_all_components_secure.jpg)

## 8. Join the two halves and close the case

1. Bring the two wires from the back piece (HDMI, and the 12V DC power
   pigtail from step 3) up to the front piece and plug them into the
   controller board.

   ![Back and front pieces, before connecting](images/two_halves_wires_disconnected.jpg)
   ![Back and front pieces, HDMI and power connected](images/two_halves_wires_connected.jpg)

2. Tuck the connected wires into the case, then press-fit the front
   piece onto the back piece. (You can also test everything before
   snapping them together — the fit comes apart easily if you need to
   get back in.)

   ![Front and back pieces being press-fit together](images/parts_being_press_fit_together.jpg)

3. Push the 3D-printed keycap over the power button switch/LED.

The unit is now fully assembled.

## 9. Power-on test

1. Plug the 12V DC power supply into the case's barrel jack input.
2. Connect a USB keyboard and mouse to the Pi.
3. Flip the rocker switch on.

Confirm it boots the way `docs/software-setup.md` §7's "Verifying the
round trip" describes (straight into the picker, no login prompt) before
buttoning up anything further.

![Fully assembled Lisa Mini Pi, booting](images/front_fully_assembled.jpg)

## Future revision being explored: iPad 3/4 panel + Pi 5 dual-power board

Not started, no build yet — noting the direction here so it's not lost.
A newly-acquired iPad 3/4 LCD + driver board
([AliExpress listing](https://www.aliexpress.us/item/3256808678954635.html))
and a Pi 5 dual-power board
([AliExpress listing](https://www.aliexpress.us/item/3256808543956539.html))
are being considered for a future revision, for two reasons:

- The iPad 3/4 panel's driver board runs on **5V** (unlike the current
  iPad 1/2 panel's 12V) and the panel's native resolution is higher than
  the current 1024x768 target - both a potential visual-quality
  improvement for LisaEm's display scaling and, since the driver board's
  input voltage would then match the Pi 5's own supply requirement, a
  possible way to power both from the same rail.
- The dual-power board comes in two input variants: a 12V barrel-jack
  version, and a 3.81mm 2-pin terminal version. The barrel-jack version
  could serve as the sole system input, but the 2-pin terminal version is
  the better fit for this project specifically, since it preserves room
  for a physical rocker power switch upstream (as in the wiring in this
  document) - and since the panel would now also run on 5V, this
  combination would let the whole system drop the 12V→5V buck converter
  entirely, powering the Pi and the LCD from the same 5V rail the dual-
  power board provides.

This would mean real changes to the wiring in this document (no buck
converter, different LCD controller power input) and likely to
`theme.py`'s fixed 1024x768 layout assumptions (see the main README's
"Project status") once a real target resolution is known - treat as new
exploration when it's picked up, not a drop-in swap of parts.
