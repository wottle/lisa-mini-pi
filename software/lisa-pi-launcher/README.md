# Lisa Boot Launcher

A fullscreen Raspberry Pi kiosk app styled after the Apple Lisa's hardware
self-test/startup screen. Appears immediately after boot and lets you pick
which vintage computer environment to start (currently LisaEm; Basilisk II
planned).

See `docs/superpowers/specs/2026-09-16-lisa-boot-launcher-design.md` for
the full design rationale.

## Running it standalone (development)

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 gen_icons.py   # only needed once, or after changing an icon
python3 launcher.py
```

Press Escape... actually there is no Escape/quit binding by design (it's a
kiosk); use Ctrl+C in the terminal you launched it from during development,
or `S`/`R`/`Q` to shut down/reboot/quit on real hardware. Note `Q` just
exits the Python process - under `launcher.service`'s `Restart=always` (see
below), systemd respawns the kiosk within a couple seconds rather than
leaving a desktop session up; it's meant as a quick dev/testing exit, not
a real "switch to desktop" feature.

## Configuration

Edit `config.json` to add/remove systems. Each entry needs `id`, `name`,
`subtitle`, `icon` (path to a PNG), and `command` (an argv list, not a
shell string) that blocks until the emulator exits.

## Controls

- Left/Right arrow: change selection
- Enter: launch the selected system
- S: shut down the Pi
- R: reboot the Pi
- Q: quit the launcher process (see the caveat above about `Restart=always`)

## Running the tests

```
python3 -m pytest
```

## Installing as the boot-time kiosk

See `system/launcher.service` and the "Display/session integration"
section of the design spec for the minimal-X11-session autostart setup.
