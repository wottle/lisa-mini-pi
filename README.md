# Lisa Mini Pi

A Raspberry Pi in a 3D-printed Apple Lisa-shaped case with a 1024x768 HDMI
LCD panel, booting straight into a kiosk launcher that lets you pick which
vintage system to run: Apple Lisa (via a patched `LisaEm`), classic Mac OS
(via Basilisk II or Mini vMac), and more planned.

## Layout

- `hardware/3d-models/` — case/enclosure 3D model files (placeholder, not yet populated).
- `hardware/assembly/` — build/assembly instructions (placeholder, not yet populated).
- `software/lisa-pi-launcher/` — the kiosk launcher (Python), including the
  GPIO power-button/LED scripts and the systemd units that run it on boot.
- `docs/software-setup.md` — end-to-end setup guide: building the patched
  LisaEm, installing the launcher, wiring the physical power button/LED,
  and the boot-time systemd setup.

## Related repos

- [`wottle/lisaem`](https://github.com/wottle/lisaem) (branch
  `lisa-fixes-1024x768`) — patched fork of `arcanebyte/lisaem` used for the
  Apple Lisa environment. See `docs/software-setup.md` for what's patched
  and why.
