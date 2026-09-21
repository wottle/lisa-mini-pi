# Lisa-style boot launcher — design spec

## Purpose

A fullscreen Raspberry Pi application that appears immediately after boot and
lets the user choose which vintage computer environment to start (currently
just LisaEm running Lisa Office System; Basilisk II + classic Mac OS images
planned later). It must not look like a modern launcher with a retro skin —
it should look like an authentic early-1980s Apple Lisa hardware self-test /
startup screen that has been repurposed as an emulator selector. Someone
familiar with a real Lisa should initially think they're looking at an
obscure Lisa ROM diagnostic screen; only after reading the system names
should it become apparent this is an emulator picker.

Reference image: a real Lisa `TESTING...` diagnostic screen — thin white
strip across the very top (small right-aligned status character); a
diagonal-hatched 1-bit dither pattern filling the background; a white panel
near the top with a thin black border and a black drop-shadow offset to its
bottom-right; small bitmap text `TESTING...` in the panel's upper-left; four
items spaced horizontally (CPU / MEM / I/O / a fourth, unlabeled/untested
icon), each with a label above the icon and a status glyph below it
(checkmark for CPU, blank for not-yet-tested); the active item (`MEM`) shown
as a solid black rectangle containing the icon and label in white
(reverse video) rather than any border/checkmark/color highlight.

## Non-goals

- No historical accuracy beyond visual style — this is not a Lisa ROM
  reimplementation, just a startup-screen-styled picker.
- No support for anything beyond LisaEm at first; Basilisk II/Mac OS 6-7 is
  a follow-on once this works and a config entry is added.
- No mouse-first design — keyboard (arrows + Enter) is primary; mouse
  support may exist but isn't the design driver.
- No modern UI conventions anywhere: no antialiasing, gradients,
  transparency, rounded rects, colored highlights, checkmarks/radio buttons
  for selection, or animation easing.

## Target environment

- Raspberry Pi (4, currently; should also work on the 3B), 1024x768 4:3
  panel, fullscreen, no window decorations, no visible terminal, no Linux
  desktop chrome ever visible during normal operation.
- Runs inside a minimal X11 session (see "Display/session integration"
  below) — chosen over a true framebuffer/KMSDRM approach specifically
  because LisaEm (and later Basilisk II) are GTK/wx apps that need a real
  X11 session anyway; unifying launcher and emulators on one graphics stack
  avoids a fragile teardown/reinit handoff between two different display
  backends.

## Components

- `launcher.py` — the pygame application. Single process, single event
  loop, no threads. Owns the boot-diagnostic animation, the selection
  screen, and the launch/wait/return cycle. Subprocess launches are
  blocking (`subprocess.run`), which is exactly the desired behavior: the
  launcher freezes on `STARTING...` until the emulator exits, then
  redraws the selection screen — no polling, no background state.
- `config.json` — the list of available systems (id, display name,
  subtitle, icon path, launch command). Loaded once at startup. Adding a
  new system (e.g. Basilisk II) later is a config-only change, no code
  change required as long as the command is a simple argv list.
- `gen_icons.py` — a one-time build-time script (Pillow) that procedurally
  draws each 1-bit icon (Macintosh/Lisa/NeXT/Apple II/PC silhouettes, plus
  the CPU/MEM/I-O/disk diagnostic glyphs and their checkmark/status marks)
  as small geometric shapes (rects/lines), saving them as PNGs into
  `icons/`. Run once during development (or re-run if icons need
  tweaking) — not part of the runtime path. This avoids hand-authoring
  pixel art blind; simple procedural geometric icons also better match the
  "tiny ROM diagnostic icon" aesthetic than sourced artwork would.
- A hand-rolled bitmap font: a Python dict mapping each character to a
  small (5x7 or 6x8) pixel grid, rendered by blitting pixels directly —
  not a TTF/system font. This sidesteps font licensing and download
  concerns for an offline kiosk boot, and guarantees the hard-edged,
  zero-antialiasing look the whole design depends on.
- `system/launcher.service` — systemd unit with `Restart=always`, launched
  within the minimal X session (see below).

## Rendering approach

- Render everything to a low-resolution logical surface — 512x384 (exactly
  half of the 1024x768 target) — using only pure black/white pixels, then
  scale up to the real screen with nearest-neighbor
  (`pygame.transform.scale`, never `smoothscale`) for the authentic chunky
  pixel look.
- All layout numbers centralized as module-level constants in
  `launcher.py`: `SCREEN_WIDTH`, `SCREEN_HEIGHT`, `PANEL_X`, `PANEL_Y`,
  `PANEL_WIDTH`, `PANEL_HEIGHT`, `ICON_SIZE`, `ICON_SPACING`, `FONT_SIZE`,
  plus a `LOGICAL_WIDTH`/`LOGICAL_HEIGHT` pair for the pre-scale surface.
- Background: a small tileable 1-bit diagonal-hatch pattern (a 4x4 or 8x8
  tile) blitted repeatedly across the whole background.
- Top strip: a thin white bar across the very top of the logical surface,
  with a single small right-aligned status character (can be static, or
  reused later for something meaningful — not load-bearing for v1).
- Panel: white rect, 1px black border; a solid black rect drawn first,
  offset ~3-4 logical px down-and-right, to produce the drop-shadow, with
  the white panel drawn on top of it.
- Each system/diagnostic item: label text centered above a fixed-size icon
  box, with a status glyph (checkmark, blank, or squiggle) below it,
  spaced horizontally across the panel — matching the reference's
  label-above/icon/status-below arrangement.
- Selection/active state: the entire item's bounding box (label + icon +
  status area) is filled solid black with all its content redrawn in
  white — full reverse video, matching the reference's `MEM` treatment.
  No border, glow, color, checkmark, or radio button is ever used for
  selection.

## State machine

1. **Boot diagnostic** (~1.5s total, tunable constant): panel shows
   `TESTING...`; four fixed diagnostic icons (CPU / MEM / I/O / DISK)
   appear; a reverse-video "currently testing" highlight sweeps across
   them in sequence, left to right, each getting a checkmark once "done"
   (fixed short delay per item, no real hardware testing implied).
2. **Selection screen**: diagnostic icons are replaced by the configured
   systems from `config.json`; panel text changes to `SELECT SYSTEM...`;
   first system is selected by default (reverse video).
   - Left/Right arrow: move selection to the previous/next system
     (wrapping or clamping — clamping matches the reference's fixed
     4-item layout better; decide during implementation).
   - While a system is selected, panel text may optionally show its name
     and subtitle (e.g. `MACINTOSH` / `SYSTEM 7.5.5`) instead of the
     static `SELECT SYSTEM...` — exact wording matches the system's
     `name`/`subtitle` config fields.
   - `S`: shut down the Pi. `R`: reboot the Pi.
3. **Launch**: Enter on a selected system sets panel text to
   `STARTING...`, then `STARTING <NAME>...`; the selected icon blinks/
   inverts briefly; the pygame window is hidden/minimized; the emulator
   subprocess is launched via `subprocess.run(command)` and the call
   blocks until it exits.
4. **Return**: once the subprocess exits, the launcher window is restored,
   the selection screen redraws, and panel text resets to
   `SELECT SYSTEM...` (the boot diagnostic does not replay).

## Configuration format

```json
{
  "systems": [
    {
      "id": "lisa",
      "name": "LISA",
      "subtitle": "OFFICE SYSTEM 3.1",
      "icon": "icons/lisa.png",
      "command": ["/home/wottle/lisaem/bin/lisaem", "-p", "-d", "-F", "-M"]
    }
  ]
}
```

`command` is a plain argv list (not a shell string) so `subprocess.run`
can invoke it directly without shell quoting concerns. Additional systems
(Basilisk II, etc.) are added as further entries in the `systems` array —
no code changes needed as long as the command is a simple argv list that
exits when the user quits the emulator.

## Display/session integration

- The Pi boots to a minimal X11 session — autologin (via
  `raspi-config`-equivalent or a systemd override) plus `xinit`/`startx`
  launching a bare session with no panel, no desktop icons, and no window
  manager chrome (either no window manager at all, or a minimal one like
  `openbox` configured with zero decorations) — never the normal
  Raspberry Pi Desktop session.
- `launcher.py` runs as an ordinary fullscreen SDL/X11 window
  (`SDL_VIDEODRIVER=x11`) within that session.
- LisaEm (and later Basilisk II) launch as ordinary subprocesses in the
  same `DISPLAY=:0` session — the same pattern already proven working for
  LisaEm on this hardware (`DISPLAY=:0 lisaem -p -d -F -M`).
- `launcher.service` (systemd, `Restart=always`) supervises `launcher.py`
  within that X session as the safety net requested — a launcher crash
  respawns it in place rather than dropping to a bare console or the
  normal desktop.
- `S`/`R` (shutdown/reboot) need to work without a sudo password prompt
  from within the kiosk session — a small polkit rule or a narrowly-scoped
  passwordless sudo entry limited to `systemctl poweroff`/`systemctl
  reboot` for this specific user, decided during implementation.

## Project structure

```
lisa-pi-launcher/
    launcher.py
    gen_icons.py
    config.json
    fonts/                  (if any bitmap font data files are needed;
                              likely just a .py module instead)
    icons/
        macintosh.png
        lisa.png
        next.png
        apple2.png
        ibmpc.png
        diag_cpu.png / diag_mem.png / diag_io.png / diag_disk.png
    system/
        launcher.service
    docs/superpowers/specs/
        2026-09-16-lisa-boot-launcher-design.md   (this file)
    README.md
```

## Testing approach

This is a fullscreen visual/input-driven application with no meaningful
headless test surface, so testing is manual, on the actual Pi hardware:

- Boot-diagnostic animation timing and visual correctness (checkmarks
  appear in sequence, ~1.5s total).
- Arrow-key navigation moves the reverse-video selection correctly across
  all configured systems, including at the first/last item.
- Enter correctly transitions through `STARTING...` →
  `STARTING <NAME>...`, launches LisaEm, and blocks until it exits.
- After LisaEm exits, the launcher correctly redraws to
  `SELECT SYSTEM...` with no leftover state from the previous launch.
- `S`/`R` correctly shut down/reboot the Pi without a password prompt
  hanging the kiosk.
- `systemctl restart launcher` (or killing the process) confirms
  `Restart=always` respawns it inside the same X session.
- A full reboot confirms autostart: the Linux desktop is never visible at
  any point, the launcher appears fullscreen automatically.

## Open items to resolve during implementation

- Exact wrap-vs-clamp behavior for Left/Right arrow at the first/last
  system.
- Exact mechanism for passwordless shutdown/reboot (polkit rule vs. a
  narrowly scoped sudoers entry) — whichever is more standard for a
  current Raspberry Pi OS Trixie image.
- Whether the top-strip status character is static or tied to anything
  meaningful (not load-bearing for v1; can be a fixed placeholder).
