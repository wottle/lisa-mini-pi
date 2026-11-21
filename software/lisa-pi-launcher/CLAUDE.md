# Lisa Boot Launcher — Project Notes for Claude

## Goal

A Raspberry Pi, in a 3D-printed Apple Lisa-shaped case with a 1024x768
HDMI LCD, that boots straight into a fullscreen kiosk styled after the real
Lisa's hardware self-test/diagnostic screen. From that picker the user
selects one of several vintage systems and it launches fullscreen; a
guest shutdown (or, for the systems that support it, the physical GPIO
power button) returns to the picker.

**Setup instructions for provisioning a brand-new Pi with this whole stack
live in `SETUP.md` in this repo, and in `../../docs/software-setup.md`.**
Neither one alone is complete — see "Two setup docs" below. Both are
**living documents** — when a step turns out to be wrong, incomplete, or
unnecessary, fix it in the same change that changes the actual setup.

### Two setup docs, not fully reconciled

`SETUP.md` (this directory) covers the launcher app, LisaEm, Basilisk II,
and Mini vMac in detail. `../../docs/software-setup.md` is the
project-wide walkthrough and is the **only** place Previous (NeXT) and
LinApple (Apple II) are documented — `SETUP.md` was never updated to
cover those two. If you're setting up a fresh Pi with all five systems,
read `docs/software-setup.md`. The two files overlap in places for the
first three systems; if you find a contradiction, the more
specific/recently-updated one is probably right.

## Current hardware baseline

Physical units, deliberately not identical:

- **Pi 4 Model B** — the primary/reference unit. Real 1024x768 HDMI LCD
  panel, physical GPIO power button + LED wired and working, all five
  emulators installed. `config.json` is shared/identical across both
  Pis (every path in it is uniform); the Pi 4 has all five `.deb`s/builds
  installed to match it.
- **Pi 3B** — secondary unit. Only LisaEm, Basilisk II, and Mini vMac are
  installed (as of 2026-09-25) — it doesn't have the power/performance
  headroom for Previous and LinApple as well. Its physical GPIO power
  button was never wired up either (powered off, not currently in active
  use). `check_deps.py` will correctly flag `next`/`apple2` as missing
  there — expected, not a bug.

- **Pi 5 (4 GB) + iPad 3/4 panel** — the unit used for the 2026-11-21
  performance work. The panel is 2048x1536 native, driven at
  **1024x768@60** (the HDMI controller board upscales; set by
  `system/xsession-launcher.sh`). Controller board make/model not
  recorded. Not measured: sustained load/thermals with the case closed.

Both run Raspberry Pi OS 64-bit (Debian 13 "trixie"), no desktop
environment at boot — a bare kiosk X11 session (`launcher.service`, see
below) owns tty1 instead.

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
openbox, then `check_deps.py` in the background, then the GPIO
power-button watcher, then `python3 launcher.py`) on `tty1`, with
`PAMName=login` + `TTYPath=/dev/tty1` etc. so it gets a real logind
session (a bare `Type=simple` unit can't switch the VT into graphics
mode). A separate `launcher-watchdog.timer` (every 30s) restarts
`launcher.service` if neither the launcher nor a known emulator process
is running — a safety net for the case where an emulator hangs on guest
shutdown or the X session dies without the launcher process itself
exiting.

`check_deps.py` (run once per kiosk session start, logs to
`~/lisa-mini-pi-dependency-check.log`) checks required/optional PATH
commands, every filesystem-path-looking argument in `config.json`'s
system commands, the installed systemd units, and the polkit rule —
always non-blocking (exits 0 regardless), so a missing optional asset
doesn't stop the kiosk from booting into whatever *does* work. Check that
log first when something that used to work stops working after moving to
a new Pi.

## Emulators wired into `config.json`

Each of the three emulators below that supports a GPIO power-button
shutdown is launched through a small `*-run-with-led.sh` wrapper (not
the binary directly) — lights GPIO18 on start, off on exit however it
exits, so the LED doubles as a "the power button will do something for
this one" indicator. Basilisk II and Mini vMac are launched directly
(no wrapper, no LED) since neither has a working button-triggered
shutdown — see below.

- **LisaEm** (`lisa-run-with-led.sh`) — this project's own fork (see the
  LisaFPGA repo's CLAUDE.md for the upstream `sint8`/signed-char
  portability bug that was found and fixed there), launched with `-k`
  (kiosk mode: fullscreen, power-on, quit-on-poweroff) `-d` (boot hard
  disk). Power button sends F12 (its power-button hotkey).
- **Basilisk II** — via apt (`basilisk2` package), System 7.5.3. Prefs at
  `~/.config/BasiliskII/prefs`; `screen dga/1024/768` (the legacy X11 DGA
  extension) for true fullscreen — `win/1024/768` just opens a floating
  1024x768 window with no fullscreen/centering, which visually looks like
  it's overlaying the desktop rather than replacing it. **`frameskip 1` is
required** (default 0 = ~11 screen updates/s on a Pi 5; 1 = ~61/s,
measured 2026-11-21; see SETUP.md §4). **No GPIO power
  button support**: upstream Basilisk II source maps a window-close
  request to a clean ADB Power keypress, but the Debian-packaged build
  actually installed here (man page dated 2002, later relinked against
  SDL2) doesn't behave that way — confirmed on real hardware (2026-09-24)
  that neither `xdotool windowclose` nor a raw `WM_DELETE_WINDOW`
  `ClientMessage` sent directly to its actual window (verified correct
  via the full X window tree) has any effect. Shut it down from inside
  the guest.
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
  rationale in `SETUP.md`. **No GPIO power button support**: this fork
  has no safe host-triggerable shutdown at all — no signal handler,
  buffered disk writes only flush on a clean exit, and its own internal
  force-quit path (Ctrl+Q+Y) is documented by the emulator itself as a
  disk-corruption risk. Shut it down from inside the guest.
- **Previous** (`previous-run-with-led.sh`) — NeXT Computer emulator,
  NeXTSTEP 3.3. Installed from a pre-built arm64 `.deb`
  (previous.nextcommunity.net) — bundles its own NeXT ROMs, no separate
  ROM sourcing needed. Has **no command-line flags at all**; everything
  (machine type, boot options, disk image) is configured once
  interactively via its own F12 settings GUI and persisted to
  `~/.config/previous/previous.cfg`. Two real gotchas hit during setup —
  see `docs/software-setup.md` §6 for full detail: `bShowConfigDialogAtStartup`
  doesn't reliably persist via the GUI (fix directly in the config file),
  and launching it directly exits after ~3s *before* a config file
  exists at all (stable once one does — a first-run-only quirk, not a
  launcher bug). Power button sends F10, its documented clean-shutdown
  key.
- **LinApple** (`linapple-run-with-led.sh`) — Apple II/II+/IIe emulator,
  boots straight into
  [Total Replay](https://archive.org/details/TotalReplay) (a single
  ProDOS hard-disk image bundling hundreds of games). Installed from a
  pre-built arm64 `.deb` (github.com/linappleii/linapple) — bundles its
  own Apple II ROMs. This beta release's arm64 `.deb` has two real
  packaging bugs on Debian trixie, both needing a manual fix after
  `apt-get install` otherwise succeeds — see `docs/software-setup.md` §7:
  `libSDL3_image.so.0` isn't declared as a dependency at all, and the
  binary links against `libzip.so.4`, which doesn't exist on trixie
  (renamed to `libzip.so.5` — fixed with a compatibility symlink, low
  risk since libzip's C API has been stable across its soname bumps).
  Power button sends F12, its quit hotkey — user-confirmed working on
  real hardware, not source-reviewed like the others (Apple II has no
  ADB/soft-power concept for this to map onto).

## Display mode, scaling and redraw (2026-11-21)

- The kiosk session sets the connected output to **1024x768@60**
  (`system/xsession-launcher.sh`); the iPad 3/4 panel's controller
  upscales. Emulators are configured for 1024x768 and render 1:1.
  `scripts/display-mode.sh native|1024|status` flips the whole stack to the
  panel's native 2048x1536 and back (marker file
  `~/.config/lisa-launcher/native-resolution`, Basilisk II
  `scale_nearest`/`scale_integer`, LisaEm `hidpi_scale` 200/100); it needs a
  `sudo systemctl restart launcher` to apply. Mini vMac is a fixed
  1024x684 build and is not changed by it. **Native was tried on
  2026-11-21 and reverted** (UI too small; Mini vMac tiny; LisaEm's Fill
  mode leaves 40 px margins at native where the mouse stops working) -
  see `docs/software-setup.md` §9. Leave the default at 1024x768.
- `theme.py` keeps the 1024x768 design as its 1x values and
  `apply_scale(w, h)` (called from `launcher.py` after the display opens)
  multiplies every size by the largest whole number that fits and centres
  the panel - 2x at 2048x1536, 1x at 1024x768. Icons are enlarged with
  nearest-neighbour to match. Unit tests reset the scale to 1x.
- `redraw.py` (`RedrawGate`) makes the main loop repaint only when
  something visible changed, on a window expose event, after an emulator
  returns, or once a second as a safety net. Before it, the launcher
  redrew every frame at 30 fps: ~48.5% of a core idle (17 ms/frame at
  2048x1536). Now ~2-3%.
- `~/.lisaem` needs `hidpi_scale=100` at a 1024x768 output (200 shows only
  a quarter of the screen). Basilisk II needs `frameskip 1`.
- LisaEm's Fill mode has a local patch (2026-11-21) in the
  `lisaem-fixes-src` tree: centre from the client area, clamp the pointer
  to the picture edge. Binary installed, original saved as
  `bin/lisaem.orig-20261121`; source change uncommitted. Virtual-display
  tested only until the author confirms on the panel. See SETUP.md Known
  gaps.

## Auto-start (2026-11-21)

- `A` on the highlighted system marks it to start by itself at power-on
  (`AUTO` tag in the card's top-right corner, "A AUTO" footer hint); `A` on
  the marked one clears it; one mark at most. Stored per machine in
  `~/.config/lisa-launcher/autostart`, not in `config.json`.
- Once per power-on, by design: `autostart.AutoStart.startup()` notes the
  boot id in `last-boot-id` the first time the launcher starts in a boot,
  *before* launching, so a watchdog or service restart in the same boot shows
  the picker and never retries an emulator that may be a corrupt install. No
  countdown or cancel window (the author chose straight into the emulator).
- Anything odd (damaged file, unknown system id, unreadable or unwritable
  boot note) means show the picker. Tests: `tests/test_autostart.py`,
  `tests/test_autostart_ui.py`, and `tests/test_launcher_autostart.py`, which
  drives the real `launcher.main()` under the dummy video driver.

## Known open items

- Basilisk II's DGA fullscreen mode was reinstated after the process-group
  signal crash bug (fixed via `start_new_session=True` in
  `_launch_selected`) turned out to be the actual cause of an earlier DGA
  crash, not DGA itself — should be retested on real hardware over a
  longer session to build confidence before calling it fully solved.
- Mini vMac's resolution is fixed at build time (512x342 native, 2x
  magnified to 1024x684, hardcoded for the real 1024x768 target panel) —
  unlike the launcher's own rendering or LisaEm/Basilisk II's fullscreen
  modes, it doesn't adapt to whatever display is actually connected.
- **`Q` (kiosk → full Raspberry Pi Desktop, and back via the "Emulator
  Launcher" desktop icon) works fully on Pi 3B, but the return trip is
  broken on Pi 4** (2026-09-22 through 2026-09-24 investigation). Tearing
  down the desktop's live Xorg session and starting the kiosk's back-to-back
  reliably triggers a kernel `WARNING` in `drivers/gpu/drm/vc4/vc4_hvs.c`
  (`__vc4_hvs_stop_channel`), leaving the display flickering blue/black
  until the new X session gives up and crash-loops. Confirmed
  Pi-4-specific via a direct `dmesg` reproduction (zero new kernel log
  lines on the same test on Pi 3B). Two mitigations were tried and both
  failed: a stop-then-sleep-then-start delay in `system/back-to-kiosk.sh`,
  and `max_framebuffers=1` in `config.txt` (to rule out Pi 4's
  always-enumerated-but-disconnected second HDMI output — it wasn't the
  cause). No kernel update fixing this was available as of 2026-09-22.
  **Resolution: the "Emulator Launcher" desktop icon is deliberately not
  installed on Pi 4** — `Q` itself still works fine there; use a plain
  reboot to get back into the kiosk instead. Full detail in `SETUP.md`'s
  Known Gaps and §7.
- LisaEm's mouse froze when launched via a mouse click (not Enter) from
  the picker — root-caused (2026-09-22/23) to SDL2's default
  auto-capture-on-click behavior outliving the click, not to X11 focus
  (a focus diagnostic proved LisaEm had real window-manager focus the
  whole time, ruling out two earlier fix attempts). Fixed with
  `SDL_MOUSE_AUTO_CAPTURE=0` in `launcher.py`, confirmed stable on real
  hardware.

## Hardware directions being explored (2026-09-26, not started)

The whole project (case STLs, BOM, `provision.sh`, and everything in
this codebase sized for a fixed 1024x768 4:3 panel — see `theme.py`'s
docstring) currently assumes one specific build: Pi 4B/5, iPad 1/2 LCD
panel. Three changes are being explored, none started yet as of that date (see the first bullet for what has changed since):

- **An iPad 3/4 LCD panel** for higher resolution than the current
  iPad 1/2 panel — **update 2026-11-21: the author's Pi 5 build now uses
  one (2048x1536), driven at 1024x768 so the launcher and emulators are
  unchanged; `theme.py` also scales to the real screen size.** Whether
  the case needed new geometry is not recorded here.
- **Fitting a Pi 5 in the case alongside a power regulation board**,
  replacing the current external 12V buck-converter setup — hardware
  only, no software impact expected.
- **An 11.6" widescreen LCD front panel** — this one *does* need real
  software work, not just a case redesign: the picker's whole layout is
  hardcoded for 1024x768 4:3 (`theme.py`), so fitting the Pi's actual
  4:3-ish display area into a widescreen opening correctly (letterboxed?
  stretched? a genuinely widescreen relayout?) is an open design
  question, not just a resolution constant to bump.

If asked to work on any of these, treat it as new exploration, not a
small tweak to the existing fixed-1024x768 assumption baked throughout
`theme.py` and the case files — check in on the actual direction before
assuming which of the above (or something else) is being pursued.
