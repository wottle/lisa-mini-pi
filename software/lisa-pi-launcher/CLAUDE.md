# Lisa Boot Launcher — Project Notes for Claude

## Goal

A Raspberry Pi 4, in a 3D-printed Apple Lisa-shaped case with a 1024x768
HDMI LCD, that boots straight into a fullscreen kiosk styled after the real
Lisa's hardware self-test/diagnostic screen. From that picker the user
selects one of several vintage systems (Apple Lisa via LisaEm, classic
Mac OS via Basilisk II and Mini vMac, more planned) and it launches
fullscreen; shutting the guest down returns to the picker.

**Setup instructions for provisioning a brand-new Pi with this whole stack
live in `SETUP.md` in this repo.** That file is the authoritative,
continuously-updated record of what a fresh install requires — update it
whenever a setup step changes, a new dependency is added, or a step turns
out to be wrong/unnecessary. Don't let it drift from what `main` actually
needs.

## Current hardware/software baseline

- Raspberry Pi 4 Model B, Raspberry Pi OS 64-bit (Debian 13 "trixie")
- No desktop environment running at boot — a bare kiosk X11 session
  (`launcher.service`, see below) owns tty1 instead
- Display currently under test: a 1920x1080/1920x1280 dev monitor. The
  real target panel is a 1024x768 HDMI LCD (repurposed iPad 2 panel), not
  yet connected — anything sized for "the real display" in this project
  means 1024x768, even though it currently renders letterboxed/smaller on
  the bigger dev monitor.

## Kiosk session architecture

No window manager at all was tried first and caused real, hard-to-diagnose
bugs (keyboard focus not transferring to newly-launched emulator windows,
and not transferring back to the picker afterward) — X11 has no window
manager to broker focus handoff without one. **Openbox** (not matchbox —
matchbox doesn't correctly implement EWMH `_NET_WM_STATE_FULLSCREEN`,
which broke LisaEm's F11 leave-fullscreen) now runs undecorated
(`~/.config/openbox/rc.xml` forces `decor="no"` on every window) to
broker that handoff correctly while staying visually invisible.

`launcher.service` runs `xinit` → `system/xsession-launcher.sh` (starts
openbox, then `python3 launcher.py`) on `tty1`, with `PAMName=login` +
`TTYPath=/dev/tty1` etc. so it gets a real logind session (a bare
`Type=simple` unit can't switch the VT into graphics mode). A separate
`launcher-watchdog.timer` (every 30s) restarts `launcher.service` if
neither the launcher nor a known emulator process is running — a safety
net for the case where an emulator hangs on guest shutdown (observed with
both LisaEm and Basilisk II, upstream quirk, not something the launcher
can fully prevent) or the X session dies without the launcher process
itself exiting.

## Emulators wired into `config.json`

- **LisaEm** — this project's own fork (see the LisaFPGA repo's CLAUDE.md
  for the upstream `sint8`/signed-char portability bug that was found and
  fixed there), launched with `-k` (kiosk mode: fullscreen, power-on,
  quit-on-poweroff) `-d` (boot hard disk) `-M-` (force-enable
  mouse-to-top-reveals-menu — note `-M` alone *disables* this, it's
  inverted from what the name suggests).
- **Basilisk II** — via apt (`basilisk2` package), System 7.5.3. Prefs at
  `~/.config/BasiliskII/prefs`; `screen dga/1024/768` (the legacy X11 DGA
  extension) for true fullscreen — `win/1024/768` just opens a floating
  1024x768 window with no fullscreen/centering, which visually looks like
  it's overlaying the desktop rather than replacing it.
- **Mini vMac** — NOT the official gryphel.com release (36.04): that
  version has zero Apple Partition Map awareness, so any real (non-raw)
  HD image gets rejected by the guest ROM as invalid media. Built instead
  from **github.com/erichelgeson/minivmac**, which adds real partition-map
  parsing (`-ndp 1` / `NonDiskProtect`). Also: this 2018-era codebase has
  no 64-bit-ARM `-cpu` entry, so its internal "4-byte Long" type
  (`ui5b`) silently becomes 8 bytes on this platform unless `-cpu x64` is
  passed explicitly — that mismatch caused real heap overruns and a
  broken slot-ROM checksum (which made the real Mac II ROM reject the
  emulated video card) before this was found. Full build recipe and
  rationale in `SETUP.md`.

## Known open items

- Basilisk II's DGA fullscreen mode was reinstated after the process-group
  signal crash bug (fixed via `start_new_session=True` in
  `_launch_selected`) turned out to be the actual cause of an earlier DGA
  crash, not DGA itself — should be retested on real hardware over a
  longer session to build confidence before calling it fully solved.
- NEXT and APPLE II entries in `config.json` are still `/bin/sleep 3`
  placeholders — no emulator work has been done for either.
- Mini vMac's resolution is fixed at build time (512x342 native, 2x
  magnified to 1024x684, hardcoded for the real 1024x768 target panel) —
  unlike the launcher's own rendering or LisaEm/Basilisk II's fullscreen
  modes, it doesn't adapt to whatever display is actually connected.
- **Implemented, not yet hardware-verified:** `Q` switches to the full
  Raspberry Pi Desktop (`lightdm` + labwc/rpd-labwc) and a "Back to Lisa
  Kiosk" desktop icon returns — see `SETUP.md` §7's "Q: switching to the
  full desktop and back". Built on `launcher.service`'s
  `Conflicts=lightdm.service` (starting either auto-stops the other) plus
  a polkit rule scoped to exactly `launcher.service`/
  `launcher-watchdog.timer`/`lightdm.service`. What's unverified: whether
  `lightdm` actually claims the VT cleanly right after `launcher.service`
  releases it - test this on real hardware before relying on it.
