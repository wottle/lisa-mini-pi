# Setting Up a New Pi

Step-by-step instructions for provisioning a brand-new Raspberry Pi with
this whole stack: the boot kiosk launcher plus LisaEm, Basilisk II, and
Mini vMac. This is a **living document** — when a step here turns out to
be wrong, incomplete, or unnecessary, fix it in the same change that
changes the actual setup. Don't let this drift from what a fresh Pi
actually needs.

**`../../scripts/provision.sh` automates all five emulators**, not just
the three this file covers - it's the faster path for a fresh Pi. This
file (and `../../docs/software-setup.md`) remain the reference for what
that script does and why.

**This file does not cover Previous (NeXT) or LinApple (Apple II) at
all** - those were added later and are documented only in
`../../docs/software-setup.md` §6-7, including their real
packaging/dependency gotchas on Debian trixie. If you're setting up a
system with all five emulators, read that file, not this one, for the
last two.

This directory (`software/lisa-pi-launcher/`) lives inside the
[`lisa-mini-pi`](../../README.md) umbrella repo. This file covers the
launcher app itself in detail; `../../docs/software-setup.md` is the
project-wide walkthrough (LisaEm build, GPIO power-button/LED wiring, and
how this directory fits into the boot-time systemd setup) - read that one
first if you're setting up a Pi from scratch. **These two docs currently
overlap in places and haven't been fully reconciled** - if you find a
contradiction between them, the more specific/recently-updated one is
probably right; fix the other one to match.

Every command below runs as a normal user over SSH unless marked
`(sudo)`. `sudo` commands need to be run interactively by a human, not by
an agent — an agent should hand you the exact command rather than run it.

## Hardware

- Raspberry Pi 4 Model B
- microSD card (boot media)
- The final target display is a 1024x768 HDMI LCD panel (a repurposed
  iPad 2 panel + HDMI driver board) — a Lisa-shaped 3D-printed case is
  built around it. Everything in this repo that's "sized for the real
  display" means 1024x768, even while testing on a different monitor.
- USB keyboard/mouse

## 1. Flash the OS

1. Raspberry Pi Imager → **Device**: Raspberry Pi 4 → **OS**: Raspberry
   Pi OS (64-bit), current release (Debian "trixie"-based as of this
   writing) — the **full Desktop image**, not Lite. (The kiosk itself
   doesn't need a desktop environment — see §5 — but Basilisk II's apt
   package and this guide's dependencies assume the full image's
   repositories/desktop-adjacent packages are available. Lite hasn't
   been tested with this setup.)
2. In the imager's advanced options (gear icon / Ctrl-Shift-X) before
   writing: set hostname, enable SSH (password or your public key),
   username/password, Wi-Fi if needed, locale/timezone/keyboard.
3. Write, boot, and confirm you can `ssh <user>@<host>`.

## 2. Base packages

```
sudo apt update
sudo apt install -y git build-essential python3-pip python3-venv \
  python3-pygame python3-pil \
  basilisk2 \
  openbox \
  libx11-dev x11-utils
```

- `basilisk2` is the apt package for Basilisk II — no source build
  needed.
- `python3-pygame`/`python3-pil` are used directly (system packages, not
  a venv) by the launcher on the Pi — see §6.
- `openbox` brokers window-focus handoff in the kiosk X session (see
  §5 for why a window manager is needed at all).

## 3. LisaEm

Built from source — this project's own fork
(`https://github.com/wottle/lisaem`), which has a real upstream
Linux/ARM portability fix (`typedef char sint8` is unsigned on
Linux/ARM but signed on macOS/x86, breaking every backward branch
displacement in the 68k core — fixed to `typedef signed char sint8`)
plus several UX enhancements (kiosk `-k` flag, hotkeys, Fill/Fit display
modes). Don't build the unmodified upstream `arcanebyte/lisaem` — it has
the same signed-char bug unfixed.

```
git clone https://github.com/wottle/lisaem.git ~/lisaem
```

LisaEm needs wxWidgets 3.2.1 built from source (Debian's packaged wx is
typically older/incompatible):

```
# TODO: capture the exact wxWidgets 3.2.1 source-build commands here
# next time this step is run from scratch. Known facts about the
# result: it installs to /usr/local/wx3.2.1-gtk, and /usr/local/wx3.2.1-gtk/bin
# must be on PATH before building LisaEm.
export PATH=/usr/local/wx3.2.1-gtk/bin:$PATH
cd ~/lisaem
./build.sh clean build
```

**Hardware note learned the hard way:** running a full desktop session
and a source build at the same time can lock up a memory-constrained Pi
(swap thrashing, unresponsive to SSH). Not generally an issue on a Pi 4
with adequate RAM, but if the build hangs, check `free -h` and consider
dropping to `multi-user.target` for the build.

You'll need a Lisa ROM (`boot.ROM`) and a Lisa Office System disk image
(a `.dc42` file, e.g. `lisaem-widget.dc42`) — these aren't redistributed
here; place them at `~/boot.ROM` and `~/lisaem-widget.dc42` (or update
`config.json`'s `lisa` entry to point elsewhere). LisaEm's own
`~/.lisaem`/`~/lisaem.conf` prefs files get created/updated by LisaEm
itself on first run and on every settings change.

## 4. Basilisk II

Already installed via apt (§2). You need a 68k Mac ROM and a classic Mac
OS disk image — these aren't redistributed here. Place them and edit
`~/.config/BasiliskII/prefs` (created on first run) to point at them:

```
rom /home/<user>/mac-lciii.rom
disk /home/<user>/macos753.image
screen dga/1024/768
displaycolordepth 0
ramsize 33554432
cpu 3
fpu false
nogui true
jit false
```

**`screen dga/1024/768`, not `win/1024/768`** — `win` just opens a plain
floating 1024x768 window (no fullscreen, no centering), which looks like
it's overlaying the desktop instead of replacing it. `dga` uses the
legacy X11 DGA extension for genuine exclusive fullscreen, and takes
over the *actual* live display resolution regardless of the configured
size, so it should adapt correctly once the real 1024x768 panel is
connected. (`dga` was avoided earlier in this project after a crash —
that crash turned out to be an unrelated process-group signal bug in the
launcher, since fixed; see the "Wiring it into the launcher" section.)

## 5. Mini vMac

**Do not use the official gryphel.com release (36.04).** It has zero
Apple Partition Map awareness — any real (partitioned) HD image gets
handed to the guest ROM at the wrong byte offset and rejected as
invalid media, even though the file opens and "inserts" successfully at
the host level. Build from
**[erichelgeson/minivmac](https://github.com/erichelgeson/minivmac)**
instead, which adds real partition-map parsing.

```
git clone https://github.com/erichelgeson/minivmac.git ~/minivmac-erich
cd ~/minivmac-erich
gcc -o setup_t setup/tool.c
./setup_t -t xgen -cpu x64 -m II -ndp 1 -fullscreen 1 \
  -hres 512 -vres 342 -mf 2 -magnify 1 > setup.sh
bash setup.sh
mkdir -p bld
# the generated Makefile's mk_COptions is missing include paths on this
# fork - add them (and -g for debuggability) before building:
sed -i 's/mk_COptions = -c$/mk_COptions = -c -g -Icfg\/ -Isrc\//' Makefile
make
```

Flag notes (all found by reading this fork's `setup/*.i` sources, not
guessed):
- `-t xgen`: "Generic X11" target. There is no dedicated 64-bit-ARM
  target in this 2018-era codebase (`-t larm` is 32-bit ARM only) —
  `xgen` is architecture-neutral and confirmed working.
- `-cpu x64`: **required**, and not obvious from the flag name. This
  codebase's internal "4-byte Long" type (`ui5b`) is `unsigned int` only
  when `-cpu x64` is selected; otherwise it falls back to `unsigned
  long`, which is 8 bytes on 64-bit Linux/ARM. That mismatch causes real
  heap-buffer overruns (`SetLongs`/`ReserveAllocOneBlock`) and a broken
  32-bit CRC in the video card's slot-ROM checksum routine, which makes
  the real Mac II ROM reject the emulated video card outright (black
  screen forever, CPU/interrupts running fine). Confirmed via `gdb`
  against a live process — not a theoretical concern.
- `-m II`: Mac II model (matches a Mac II ROM — see below).
- `-ndp 1`: `NonDiskProtect`, this fork's Apple Partition Map parser —
  the actual fix for the disk-rejection problem above.
- `-hres 512 -vres 342 -mf 2 -magnify 1`: native compact-Mac resolution
  (512x342), magnified 2x (1024x684) and started already magnified —
  sized for the real 1024x768 target panel (684 leaves ~84px total
  letterboxing top/bottom, since 512:342 isn't quite 4:3). On any bigger
  test monitor this will appear smaller/centered with black borders —
  expected, not a bug; it'll fill correctly on the real panel.

You'll need a Mac II ROM and a System 6-or-later disk image with a real
Apple Partition Map (a plain unpartitioned raw image also works, just
doesn't need `-ndp`). Place them and point `config.json`'s `command` at
them:

```
mkdir -p ~/minivmac-final
cp ~/minivmac-erich/minivmac ~/minivmac-final/minivmac
cp <your Mac II ROM> ~/minivmac-final/MacII.ROM
cp <your disk image> ~/minivmac-final/System6.image
```

## 6. The launcher itself

```
git clone https://github.com/wottle/lisa-mini-pi.git ~/lisa-mini-pi
cd ~/lisa-mini-pi/software/lisa-pi-launcher
python3 gen_icons.py   # generates the boot-diagnostic icons; only needed
                        # once, or after changing theme.py's ICON_SIZE
```

No venv on the Pi — it runs against the system `python3-pygame`/
`python3-pil` installed in §2. Edit `config.json` to point each system's
`command` at the binaries/ROMs/disks placed in §3-5.

## 7. Kiosk session integration

**Why a window manager at all:** a bare X11 session with no window
manager was tried first and caused real bugs — keyboard focus doesn't
reliably transfer to a newly-launched emulator's window, or back to the
picker after the emulator closes, with nothing to broker that handoff.
**Openbox**, not matchbox — matchbox (tried second) doesn't correctly
implement EWMH `_NET_WM_STATE_FULLSCREEN`, which broke LisaEm's F11
leave-fullscreen (it flipped LisaEm's internal state but never actually
resized the window).

```
mkdir -p ~/.config/openbox
cp /etc/xdg/openbox/rc.xml ~/.config/openbox/rc.xml
```

Then add a rule forcing every window undecorated (no titlebars — matches
the no-window-manager look), just before `</applications>` in that file:

```xml
  <application class="*">
    <decor>no</decor>
  </application>
```

Copy the systemd units and polkit rule from this repo's `system/`
directory, then enable them **(sudo)**:

```
sudo cp system/launcher.service system/launcher-watchdog.service \
  system/launcher-watchdog.timer /etc/systemd/system/
sudo cp system/10-lisa-launcher-power.rules /etc/polkit-1/rules.d/
sudo systemctl daemon-reload
sudo systemctl enable --now launcher.service
sudo systemctl enable --now launcher-watchdog.timer
```

- `launcher.service` runs `xinit` → `system/xsession-launcher.sh`
  (starts openbox, then `python3 launcher.py`) on `tty1`. It needs
  `PAMName=login` + `TTYPath=/dev/tty1` + `TTYReset`/`TTYVHangup`/
  `TTYVTDisallocate=yes` + `Conflicts=getty@tty1.service` — a bare
  `Type=simple` unit has no logind session, and Xorg fails immediately
  with `xf86OpenConsole: Switching VT failed` without one.
- `launcher-watchdog.timer` runs `launcher-watchdog.sh` every 30s, which
  restarts `launcher.service` if neither the launcher nor a known
  emulator process is running — covers the case where an emulator hangs
  on guest shutdown instead of exiting (an observed upstream quirk in
  both LisaEm and Basilisk II, not fully preventable from the launcher
  side) or the X session dies without the launcher process itself
  exiting. **Update `launcher-watchdog.sh`'s process list whenever
  `config.json` gains a new emulator binary name.**
- `10-lisa-launcher-power.rules` is a polkit rule letting the launcher's
  `S`/`R` keys (`systemctl poweroff`/`reboot`) run without a password
  prompt for the kiosk user, and letting `Q` and the desktop's "back to
  kiosk" icon start/stop the three specific units below without one
  either.

Reboot and confirm it boots straight into the picker with no login
prompt, no desktop flash, and that Escape/Ctrl+C don't get you out of it
(none exist by design — see the README's Controls section).

### Q: switching to the full desktop and back

`Q` needs `lightdm` (installed by the full Desktop image, §1) to still be
present but disabled at boot (`systemctl is-enabled lightdm` should say
`disabled` — the kiosk owns `tty1` at boot instead). The mechanism is
`launcher.service`'s `Conflicts=lightdm.service`: starting either service
auto-stops the other, so switching sessions is just one `systemctl start`
each way — no manual "stop the other one first" step, and no risk of both
fighting over the same VT at once.

**Only install the "Emulator Launcher" desktop icon/menu entry below on a
Pi 3B, and only if you actually want the round trip back into the kiosk
from the desktop.** On a Pi 4 + the project's 1024x768 HDMI panel, that
specific transition (tearing down the desktop's live Xorg session and
starting the kiosk's back-to-back) reliably triggers a kernel `WARNING`
in `drivers/gpu/drm/vc4/vc4_hvs.c` (`__vc4_hvs_stop_channel`) that leaves
the display flickering blue/black - confirmed via a direct `dmesg`
reproduction, and unfixed by both a delay-based workaround and
`max_framebuffers=1`; no kernel update addressing it was available as of
2026-09-22. The same transition was directly confirmed clean (zero new
kernel log lines) on a Pi 3B. `Q` (kiosk → desktop) itself isn't affected
either way and is safe to set up on any Pi - just skip the icon below on
a Pi 4 and use a plain `sudo reboot` from the desktop to get back to the
kiosk instead. (Also worth knowing before bothering with this on a
Pi 3B at all: LisaEm's performance there is poor enough - see the
project's CLAUDE.md hardware notes - that a Pi 3B usually isn't the
recommended target regardless.)

Install the "Emulator Launcher" desktop entry - as both a desktop icon and an
Applications-menu entry, since rpd-labwc's desktop-icon rendering has
been inconsistent:

```
chmod +x ~/lisa-mini-pi/software/lisa-pi-launcher/system/back-to-kiosk.sh
mkdir -p ~/Desktop ~/.local/share/applications
cp ~/lisa-mini-pi/software/lisa-pi-launcher/system/back-to-kiosk.desktop ~/Desktop/back-to-kiosk.desktop
chmod +x ~/Desktop/back-to-kiosk.desktop
cp ~/lisa-mini-pi/software/lisa-pi-launcher/system/back-to-kiosk.desktop ~/.local/share/applications/back-to-kiosk.desktop
chmod +x ~/.local/share/applications/back-to-kiosk.desktop
```

The desktop icon needs one more step, or double-clicking it prompts
"this text file appears to be an executable..." instead of launching -
PCManFM only trusts `.desktop` files created through its own UI by
default, not ones just copied in:

```
gio set ~/Desktop/back-to-kiosk.desktop "metadata::trusted" true
```

This is a per-file extended attribute, not something that survives a
fresh `cp` - re-run it if the desktop icon is ever replaced. (`back-to-
kiosk.sh` and `back-to-kiosk.desktop` ship in `system/` and get deployed
with everything else via the repo's normal rsync/copy; the commands
above are only needed the first time, to actually place/trust the icon
outside the repo's own tree.)

**Confirmed working on real hardware** (2026-09-21, Pi 3B): pressing `Q`
at the picker switches cleanly to the full desktop, and the "Emulator
Launcher" icon switches back - on a Pi 3B specifically, see the warning
above for why a Pi 4 shouldn't have the icon installed at all
(2026-09-22). If a future Pi's `lightdm` doesn't claim the VT cleanly
once `launcher.service` releases it, check `journalctl -u lightdm.service`
for what went wrong.

## 8. Verifying the round trip

For each system in `config.json`: launch it from the picker, confirm
keyboard input works both inside the emulator and back at the picker
afterward, and confirm a guest shutdown (not a force-kill) returns
cleanly to the picker. This project's history has several examples of
"launches fine" not implying "the full round trip works" — X11
focus-handoff and process-exit-on-shutdown bugs have each independently
broken this in the past.

## Known gaps (update this section as they close)

- **§3's LisaEm build instructions are for the wrong fork/branch on at
  least one real Pi.** This repo was consolidated from a previously
  separate `lisa-pi-launcher` checkout that used `wottle/lisaem`'s
  `pi4-all-enhancements` branch at `~/lisaem`; a Pi 3B set up separately
  (with the GPIO power button/LED, see `lisa-run-with-led.sh`/
  `lisa-power-button-watcher.sh` and `../../docs/software-setup.md`) uses
  `wottle/lisaem`'s `lisa-fixes-1024x768` branch at `~/lisaem-fixes-src`
  instead, which is the one with the F12 power-button hotkey the GPIO
  watcher depends on - and which needed a small additional patch (this
  branch's `-k` kiosk flag was unconditionally forcing mouse-to-top-menu
  off, with no `-M`/`-M-` flag in this branch to override it, unlike the
  other one) to keep Shut Down reachable via mouse. §3 needs rewriting to
  point at `lisa-fixes-1024x768` and drop the reference to `-M-`
  (this branch has no such flag), or the two branches need reconciling
  into one that both Pis actually use.
- LisaEm's/Basilisk II's asset-provisioning steps (§3-4) don't yet
  record exactly how `boot.ROM`/`lisaem-widget.dc42`/`mac-lciii.rom`/
  `macos753.image` were originally obtained/created for this specific
  build — fill this in next time it's done from scratch.
- The wxWidgets 3.2.1 source-build commands (§3) aren't captured yet.
- NEXT and APPLE II are now implemented (Previous and LinApple
  respectively) but only documented in `../../docs/software-setup.md`
  §6-7 - this file was never updated to cover them, see the note at the
  top.
- **Pi 3B does not get Previous or LinApple** (2026-09-25 decision) - the
  Pi 3B doesn't have the power/performance headroom for them on top of
  LisaEm/Basilisk II/Mini vMac. `config.json` is shared across both Pis
  (all paths are now uniform, no per-machine divergence needed for the
  five-system config), but the Pi 3B simply never got the two `.deb`s
  installed - `check_deps.py` correctly flags `next`/`apple2` as missing
  there, which is expected, not a bug. The Pi 3B was also powered off
  without its physical GPIO power button/LED ever being wired up, so the
  button/LED extensions for Previous/LinApple (`docs/software-setup.md`
  §2) were never tested on it either.
- Mini vMac was also added to a second Pi (`config.json` from the first Pi
  won't just work there unless the same binaries/ROMs/disks are placed at
  the same paths) — this file assumes one Pi at a time; note which
  physical unit each of your own local notes refers to.
- This file and `../../docs/software-setup.md` overlap and haven't been
  reconciled into one - see the note at the top of this file.
- **The desktop→kiosk switch (the "Emulator Launcher" icon) is unfixed on
  Pi 4 and the icon should not be installed there - see the warning in
  §7 above.** On real hardware (Pi 4 + the project's 1024x768 HDMI
  panel), tearing down the desktop's Xorg session and starting the
  kiosk's back-to-back reliably triggers a kernel `WARNING` in
  `drivers/gpu/drm/vc4/vc4_hvs.c` (`__vc4_hvs_stop_channel`, hit via the
  outgoing Xorg's `FBIOBLANK` ioctl on exit), which leaves the display
  flickering blue/black until the new X session gives up and
  crash-loops. Confirmed directly reproducible via `dmesg` on Pi 4 and
  directly confirmed NOT reproducible the same way on Pi 3B - this is
  specific to the Pi 4 hardware/kernel combination, not the launcher
  code. Two mitigations were tried and both failed to fix it: a
  stop-then-sleep-then-start delay in `system/back-to-kiosk.sh` (kept -
  harmless, but doesn't help), and `max_framebuffers=1` in config.txt (to
  rule out Pi 4's always-enumerated-but-disconnected second HDMI output's
  HVS channel as the cause - it wasn't). No kernel update fixing this was
  available as of 2026-09-22. `Q` (kiosk → desktop) itself is unaffected
  and still works fine on any Pi; a plain reboot is the way back into the
  kiosk on a Pi 4 instead of the icon.
