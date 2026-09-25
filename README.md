# Lisa Mini Pi

A Raspberry Pi in a 3D-printed Apple Lisa-shaped case with a 1024x768 HDMI
LCD panel, booting straight into a "CHOOSE YOUR ADVENTURE" kiosk launcher
that lets you pick which vintage system to run:

- **Apple Lisa** — Office System 3.1, via a patched `LisaEm`
- **Classic Mac OS 6** — via Mini vMac
- **Classic Mac OS 7** — via Basilisk II
- **NeXTSTEP 3.3** — via Previous
- **Apple II** — via LinApple, boots straight into Total Replay (a
  ready-to-play library of Apple II games)

A physical GPIO power button + LED are wired up for the systems that
support a clean button-triggered shutdown (Lisa, NeXT, Apple II) — see
`docs/software-setup.md` §2.

## Setting up a new Pi

```
git clone https://github.com/wottle/lisa-mini-pi.git ~/lisa-mini-pi
~/lisa-mini-pi/scripts/provision.sh
```

Automates everything installable without copyrighted assets - every
emulator build/install, the kiosk launcher, GPIO/LED wiring setup,
systemd units, and the boot splash. **There's no pre-packaged SD card
image**: every emulator needs a ROM and/or OS disk image that this
project has never redistributed (see "not redistributed here"
throughout `docs/software-setup.md`) - baking those into a public image
would be a real copyright problem. `provision.sh` prints exactly which
files to place where once it's done; read it before running it, like
any script that calls `sudo`.

## Layout

- `hardware/3d-models/` — case/enclosure 3D model files (placeholder, not yet populated).
- `hardware/assembly/` — build/assembly instructions (placeholder, not yet populated).
- `scripts/provision.sh` — automates the software setup below on a fresh
  Pi; see "Setting up a new Pi" above.
- `software/lisa-pi-launcher/` — the kiosk launcher (Python), including the
  GPIO power-button/LED scripts and the systemd units that run it on boot.
- `docs/software-setup.md` — end-to-end setup guide: building the patched
  LisaEm, installing every emulator, wiring the physical power
  button/LED, the boot splash, and the boot-time systemd setup.
- `software/lisa-pi-launcher/SETUP.md` — a second, older setup doc
  covering the launcher/LisaEm/Basilisk II/Mini vMac in more detail; it
  does not cover Previous or LinApple (see the note at its top).

## Related repos

- [`wottle/lisaem`](https://github.com/wottle/lisaem) (branch
  `lisa-fixes-1024x768`) — patched fork of `arcanebyte/lisaem` used for the
  Apple Lisa environment. See `docs/software-setup.md` for what's patched
  and why.
