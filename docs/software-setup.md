# Software Setup

End-to-end setup for the software side of the Lisa Mini Pi: the patched
LisaEm build, the kiosk launcher, the physical power-button/LED wiring, and
the boot-time systemd configuration that ties it all together. Five
emulators are covered: LisaEm (§1), Basilisk II (§4), Mini vMac (§5),
Previous/NeXT (§6), and LinApple/Apple II (§7).

**`../scripts/provision.sh` automates every step below** except placing
your own ROM/disk images (never redistributed here - see each section)
and the physical GPIO wiring. This file remains the reference for what
that script does and why; read a section here if a step needs more
context than the script's own comments give, or if you're doing
something by hand instead.

**Fresh-install test (2026-11-23).** I ran `provision.sh` start to finish
on a new 2 GB Raspberry Pi 4 with Raspberry Pi OS Lite 64-bit (Debian 13
"trixie"), under the user name `admin` rather than `wottle`. That run found
and fixed six problems: the install assumed a user named `wottle`; the
Lite image has no Plymouth (needed for the boot splash); `xdotool` was
never installed (the power-button watcher needs it); the low-RAM warning
fired on a 2 GB Pi 4; `git` has to be installed before the clone; and
Quit ("Q") only worked on a machine with the desktop (it started
`lightdm`, which Lite does not have, so the launcher just restarted). Quit
now falls back to a text console login when there is no `lightdm`. I have
unit-tested that choice, but have not yet tried it at the panel. After
placing my own ROM and disk images, all five systems launched from the
picker and worked. LisaEm needed the identity fix above, because I used a
disk image that had already been installed. I did not try the GPIO
power button until afterwards, when I connected an LED and a switch to
the GPIO pins on the bench; it worked as expected. I did not test it in
a closed case.

**Pi 3B note (as of 2026-09-25):** only LisaEm, Basilisk II, and Mini
vMac are installed on the project's Pi 3B - it doesn't have the
power/performance headroom for Previous and LinApple as well. `config.json`
is shared/identical across both Pis (every path in it is now uniform), so
this is purely about which `.deb`s got installed where, not a config
difference. `check_deps.py` will correctly flag `next`/`apple2` as
missing on a Pi 3B set up this way - that's expected, not a bug to fix.

## 1. Apple Lisa emulation: building the patched LisaEm

The stock `arcanebyte/lisaem` has a couple of Linux/ARM-specific bugs.
`wottle/lisaem` (branch `pi4-lisa-fixes`) carries the fixes on top of
`arcanebyte/lisaem`'s `master`, including:

> **One branch for every build (2026-11-21).** The Pi 5 originally ran the
> `lisa-fixes-1024x768` branch and the Lisa Mini ran a separate
> `pi4-all-enhancements` line (Fit to Window mode, real Apple-key shortcuts, a
> `-M`/`--no-topmenu` preference, and 68k/floppy/video-latch fixes). I merged
> them into `pi4-lisa-fixes`: that line plus my Fill-mode pointer-clamp fix
> and the F12 power-key handler. `lisa-fixes-1024x768` is left in the fork as
> history. The list below was written for the older branch; `pi4-lisa-fixes`
> has its own versions of the Fill mode and signed-char fixes. On 2026-11-21 I
> also merged `arcanebyte/lisaem` `master` (27 commits) into it; the fork's
> `master` is now a plain mirror of upstream, so updating is a
> `git merge upstream/master` into `pi4-lisa-fixes`. **Built and run on the
> Lisa Mini (Pi 4) and rebuilt on the Pi 5; on the Pi 5 I checked Fill mode and
> the power button only. I have not run a fresh `provision.sh` against it.** I did not check whether the older branch's HQX
> 3.5x display fix is covered. On the Pi 4, changing the emulated CPU speed
> from the menu can stall the window for a while before it recovers (also seen
> before the merge; I did not measure how long or find the cause), so I set a
> speed once and leave it.

- The Power Button menu item never had a working keyboard shortcut, on any
  platform — menu labels alone don't create working accelerators in this
  app, because its keyboard-capture code (`LisaWin::OnChar`/`OnKeyDown`)
  steals all keyboard input for Lisa emulation before wx's own
  menu-accelerator dispatch ever sees it. F12 and Ctrl+Alt+P are now wired
  up the same way the existing F11/zoom shortcuts already were: as
  hardcoded key checks in `OnChar`. This is what the GPIO power button
  (see below) actually presses.

### Build prerequisites

```bash
sudo apt install -y xserver-xorg xinit x11-xserver-utils openbox
```

wxWidgets 3.2.1 needs to be built from source into `/usr/local/wx3.2.1-gtk`
(the stock Raspberry Pi OS package is too old). See the upstream LisaEm
build docs for the wxWidgets build steps; once it's in place:

```bash
export PATH=/usr/local/wx3.2.1-gtk/bin:$PATH
```

### Building

```bash
git clone --branch pi4-lisa-fixes https://github.com/wottle/lisaem.git ~/lisaem-fixes-src
cd ~/lisaem-fixes-src
export PATH=/usr/local/wx3.2.1-gtk/bin:$PATH
./build.sh clean build
```

A full `clean build` takes roughly 10-12 minutes on a Raspberry Pi 3B.
Incremental `./build.sh build` after touching a single `.cpp` file is much
faster (a few minutes).

**Memory warning (Pi 3B, 1GB RAM):** running a full desktop session and a
build at the same time can lock the Pi up hard enough to need a physical
power cycle. Before a `clean build`, drop to a text console first:

```bash
sudo systemctl isolate multi-user.target
# ... build ...
sudo systemctl isolate graphical.target
```

An incremental single-file rebuild is light enough to usually be fine
without dropping to console, but watch `free -h` if in doubt.

The resulting binary is `~/lisaem-fixes-src/bin/lisaem`.

### Required launch environment

LisaEm must be launched with `GDK_BACKEND=x11` explicitly set. Without it,
GTK prefers native Wayland whenever `WAYLAND_DISPLAY` is set (even with
`DISPLAY` also set), which makes LisaEm's window invisible to X11 tools
like `xdotool` — which the power-button watcher depends on to send it the
F12 keypress.

### Reusing an existing Lisa disk image (Error 10738)

`provision.sh` seeds `~/lisaem.conf` with LisaEm's blank hardware identity
(`serialnumber=ff000000...`, an all-zero `[pram]` block). That is right for
a Lisa Office System installed fresh from floppies, which sets up its own
identity on first boot. A disk image that has already booted on another
LisaEm remembers *that* identity and refuses a different one with
**Error 10738** ("Checksum failure or too many hardware config changes").

**Seen on a fresh install (2026-11-23).** I set up a Pi 4 from scratch with
`provision.sh` and dropped in the `lisaem-widget.dc42` from my Pi 5. LisaEm
showed Error 10738 on the first launch. The other four systems worked.

**The fix that worked:** take `~/lisaem.conf` from the machine the disk
already boots on, change its paths to this Pi's home directory, and use it
in place of the seeded one:

```
scp otherpi:lisaem.conf /tmp/lisaem.conf
sed -i "s|/home/otheruser|$HOME|g" /tmp/lisaem.conf
cp ~/lisaem.conf ~/lisaem.conf.provisioned      # keep the seeded one
cp /tmp/lisaem.conf ~/lisaem.conf
```

That brought over the serial number, the `[pram]` and `[clock]` blocks and
a few model settings (`ioromver`, `hle`, `4mbmacworks`) in one go. I did
not try copying only `serialnumber` and `[pram]` (which
`software/lisa-pi-launcher/SETUP.md` suggests is enough), so I can't say
whether that alone would have worked. Make the change while LisaEm is not
running. It rewrites its config files when it exits, so a change made
while it is open can be overwritten.

## 2. GPIO power button and LED

Full pinout diagram: `hardware/pi-wiring-diagram.svg` (also covers the
buck-converter power wiring below).

Hardware wiring:

- **Pi power**: the 12V→5V buck converter's output feeds the Pi directly
  through the GPIO header — 5V into **Pin 2**, ground into **Pin 6** —
  not through the USB-C/micro-USB port. This bypasses the Pi's USB input
  protection, so the supply must be a clean, regulated 5V/3A+ source, and
  **USB power must never be connected at the same time** as GPIO power.
- **LED** (status/power indicator): 3.3V logic from GPIO18 (**Pin 12**) →
  resistor (330Ω) → LED → GND (**Pin 14**), GPIO18 driven directly as an
  output (high = on). 330Ω limits LED current to roughly 4mA at 3.3V for
  a typical LED — recalculate if using a different LED's forward voltage/
  current rating.
- **Power button switch**: 3.3V (**Pin 1**) → resistor (330Ω) → switch →
  GPIO17 (**Pin 11**), configured as an input with the internal
  pull-down enabled, so it reads a clean low when open and high when the
  switch closes (pressed).

```bash
pinctrl set 18 op dl      # LED off by default
pinctrl set 17 ip pd      # button input, pull-down
```

GPIO tooling used: `pinctrl` (state changes) and `gpiomon`/`gpiodetect`
(from `gpiod`/`libgpiod`, edge detection) — both ship with current
Raspberry Pi OS.

### `lisa-run-with-led.sh`

Launches LisaEm, turning the LED on for as long as it's running:

```bash
software/lisa-pi-launcher/lisa-run-with-led.sh -k -d
```

(`-k`: kiosk mode - power on immediately, fullscreen, quit the process
once the Lisa powers off; `-d`: boot from the ProFile/Widget drive. This
is also exactly what `config.json`'s `lisa` entry passes, so the button
and the launcher menu behave identically.)

**`-k` on the older `lisa-fixes-1024x768` branch used to unconditionally force
mouse-to-top-reveals-menu off** - fine for a picker with no other UI, but
on a kiosk with no titlebar/window-manager chrome, that's the *only* way
to reach the Special/Shut Down menu without a keyboard, so it's been
patched to leave that setting at its saved default (on) instead. There's
no `-M`/`-M-` flag on that branch to fix it via the command line (the
`pi4-lisa-fixes` branch has one, but the launcher still passes plain `-k -d`,
which works on the Lisa Mini) - see the patch note in
`software/lisa-pi-launcher/SETUP.md`'s Known Gaps if rebuilding from a
clean checkout of this branch.

### `lisa-power-button-watcher.sh`

A **persistent** watcher — meant to run for the entire time the Pi is on,
independent of whether the launcher menu or an emulator is currently
showing (started once, alongside `openbox`, in
`system/xsession-launcher.sh`; see below). On each GPIO17 press, it
dispatches to whichever emulator (if any) is currently running:

- **LisaEm**: sends F12 (its power-button hotkey), via `lisa-run-with-led.sh`.
- **Previous**: sends F10, its documented clean-shutdown key (§6), via
  `previous-run-with-led.sh`.
- **LinApple**: sends F12, its quit hotkey, via `linapple-run-with-led.sh`.
  User-confirmed on real hardware (2026-09-24) that this cleanly quits
  LinApple, unlike the other two below - not source-reviewed the way
  Basilisk II/Mini vMac were, since Apple II has no ADB/soft-power
  concept for F12 to map onto; it's simply LinApple's own quit binding.
- **Basilisk II and Mini vMac**: deliberately *not* handled — the button
  press is ignored while either is running. Upstream Basilisk II source
  (`src/SDL/video_sdl.cpp` in `cebix/macemu`) maps a window-close request
  to a genuine ADB Power keypress (`ADBKeyDown(0x7f)`/`ADBKeyUp(0x7f)`),
  which would be exactly what we want — **but the actual Debian-packaged
  `basilisk2` build doesn't behave this way**: confirmed on real hardware
  (2026-09-24) that neither `xdotool windowclose` nor a raw
  `WM_DELETE_WINDOW` `ClientMessage` sent directly to its actual window
  (verified correct via the full X window tree, not guessed) has any
  effect at all - the package is apparently built from an older codebase
  (its man page is dated 2002) later relinked against SDL2, whose event
  handling doesn't match the modern upstream fork's source. This fork of
  Mini vMac has no safe host-triggerable shutdown at all either (no
  signal handler, buffered disk writes only flushed on a clean exit, and
  its own force-quit path is documented by the emulator itself as a
  disk-corruption risk). Shut both of these down from inside the guest
  instead.
- **Nothing running** (the launcher menu is showing): launches LisaEm
  via `lisa-run-with-led.sh` — the button "powers on" the Lisa.

All three LED wrapper scripts (`lisa-run-with-led.sh`,
`previous-run-with-led.sh`, `linapple-run-with-led.sh`) follow the same
pattern: light GPIO18 on start, turn it off on exit (however it exits),
so the LED doubles as a visual "the power button will do something for
this emulator" indicator - deliberately not wired up for Basilisk II or
Mini vMac, matching the button itself.

**A bare `SIGTERM`/kill to any of these processes was deliberately never
considered as a shutdown mechanism** — for Mini vMac specifically it's
actively unsafe (unflushed buffered disk writes); for Basilisk II it's a
lower-risk fallback if you want it (no signal handler, but disk writes
are raw unbuffered syscalls, so the actual risk is closer to unplugging
a real un-shutdown Mac than to real data loss) but isn't wired up here by
choice; for all of them it skips the guest OS's own clean-shutdown
sequence, which is the whole
point of a power button in the first place.

Key detail: it sends the keypress via a plain, untargeted `xdotool key`
(XTEST-based), relying on LisaEm already having input focus by default as
the only real window in the kiosk session. Earlier attempts to explicitly
focus/activate the window first (`xdotool windowfocus`, `xdotool
windowactivate`) both failed with X protocol errors in this openbox-managed
session — the untargeted approach is what actually works reliably here.

## 3. The kiosk launcher

See `software/lisa-pi-launcher/README.md` and `SETUP.md` for the launcher
app itself (configuration format, controls, running it standalone for
development).

### Boot-time integration

The launcher runs as `launcher.service` (see `system/launcher.service`),
which:

- Takes over `/dev/tty1` directly (`PAMName=login`, `TTYPath=/dev/tty1`,
  `Conflicts=getty@tty1.service`) so it can start its own X session without
  needing a normal login session.
- Starts `openbox` and this project's power-button watcher, then runs
  `launcher.py` (see `system/xsession-launcher.sh`). The same script sets
  the connected HDMI output to 1024x768@60 first (see §9).
- `Restart=always` respawns the kiosk if it or an emulator it launched
  ever crashes out to a shell.

**Important:** this conflicts with the normal desktop (`lightdm`) for
control of `tty1` — both will crash-loop if left enabled together. The
kiosk launcher is meant to fully replace the desktop on boot:

```bash
sudo systemctl disable --now lightdm
sudo systemctl enable --now launcher.service launcher-watchdog.timer
```

`system/10-lisa-launcher-power.rules` is a polkit rule allowing the
launcher's own shutdown/reboot keys (`S`/`R`) to work without
authentication, including while a second session (e.g. an SSH login used
to administer the Pi) is also active.

### Auto-start at power-on

Highlight a system in the picker and press `A` to mark it as the one that
starts by itself at power-on (an `AUTO` tag appears in its card's top-right
corner; `A` again on it clears the mark; only one system can be marked).
On the next power-on the launcher goes straight into it, with no countdown.

It is deliberately **once per power-on**: the launcher notes Linux's
per-boot id (`/proc/sys/kernel/random/boot_id`) in
`~/.config/lisa-launcher/last-boot-id` the first time it starts in each
boot, *before* launching anything. A later start in the same boot - the
watchdog restarting the launcher after an emulator hangs, coming back from
the desktop, a `systemctl restart launcher` - therefore shows the picker
and never retries the emulator, which could be a corrupt install. A reboot
(`R`) or power cycle is a new boot, so it auto-starts again. Exiting the
emulator returns to the picker as usual.

The mark is per machine, in `~/.config/lisa-launcher/autostart` (the
system's `id`), not in `config.json`, which is shared and committed. If the
file is unreadable, names a system that is no longer in `config.json`, or
the boot id can't be read or noted, the launcher shows the picker. Delete
the file to clear the mark by hand. The logic is in `autostart.py`; its
tests, and the tests that drive the real launcher loop, are
`tests/test_autostart.py`, `tests/test_autostart_ui.py` and
`tests/test_launcher_autostart.py`.

## 4. Basilisk II (classic Mac OS, System 7.5.3)

Full install/build steps are in
`software/lisa-pi-launcher/SETUP.md` §4, not duplicated here. Installed
at `/usr/bin/BasiliskII` via `apt install basilisk2`, launched by the
launcher with no extra flags — see `config.json`.

**Set `frameskip 1` in `~/.config/BasiliskII/prefs`** (`provision.sh`
writes it for a new Pi). The default gives only ~11 screen updates per
second on a Pi 5, which makes the pointer and drawing jerky; `frameskip 1`
gives ~61/s. Details and what made no difference: §9.

**GPIO power button**: not wired up (§2 above) - the Debian-packaged
build doesn't respond to a clean window-close/ADB-power-key request the
way upstream Basilisk II's own source does (confirmed on real hardware,
2026-09-24 - see §2's watcher script notes). Shut it down from inside
the guest instead.

## 5. Mini vMac (classic Mac OS, System 6.0.8)

Full install/build steps (including the `-cpu x64`/`-ndp 1` flags and
why they're required) are in `software/lisa-pi-launcher/SETUP.md` §5,
not duplicated here. Installed at `~/minivmac-final/`, launched by the
launcher with a specific ROM and System 6 disk image — see
`config.json`.

**GPIO power button**: not wired up (§2 above) - this fork has no safe
host-triggerable shutdown at all (no signal handler; buffered disk
writes only flush on a clean exit; its own internal force-quit path is
documented by the emulator itself as a disk-corruption risk). Shut it
down from inside the guest instead.

## 6. Previous (NeXT Computer, NeXTSTEP 3.3)

Installed from a pre-built `.deb`, not built from source - the project's
GitHub/SourceForge source build needs SDL3 built from source on top of
CMake, and a pre-built package already exists for arm64:

```
curl -LO http://previous.nextcommunity.net/release/previous_4.4-0wmlive1_arm64.deb
sudo apt-get install -y ./previous_4.4-0wmlive1_arm64.deb
```

This pulls in `libsdl3-0` and the rest of its dependencies from Debian's
own repos automatically - no manual SDL3 build needed. The package also
**bundles NeXT ROM images** (`/usr/share/previous/Rev_3.3_v74.BIN`,
etc.) - no separate ROM sourcing required, unlike LisaEm/Basilisk
II/Mini vMac.

Previous has **no command-line flags at all** - `previous.1`'s man page
says so explicitly. Everything (machine type, ROM selection, boot
options, disk images, fullscreen) is configured interactively via an
in-app settings GUI (press **F12** while it's running), saved to
`~/.config/previous/previous.cfg`, and reloaded automatically on every
subsequent launch.

`config.json`'s `next` entry runs `previous-run-with-led.sh` (no
arguments) rather than `/usr/bin/previous` directly - it's the same
LED-on/LED-off wrapper pattern as `lisa-run-with-led.sh` for LisaEm,
lighting GPIO18 for as long as Previous is running so the LED signals
"the power button will do something" (the watcher sends Previous F10 -
see §2's `lisa-power-button-watcher.sh` section). The one-time
interactive setup below has to happen at the physical Pi (keyboard
required for a couple of steps) regardless of which of the two you
launch it with.

You'll need a NeXTSTEP disk image - not redistributed here. One-time
setup, at the Pi, with a keyboard attached:

1. Launch Previous from the picker (or run `/usr/bin/previous` directly
   for this first-run setup - the LED wrapper isn't required for setup,
   just for the LED). The settings GUI opens automatically on first
   launch.
2. Uncheck **Show at startup** - see the gotcha below, this alone isn't
   enough.
3. **System settings → Machine Type**: `NeXTstation` (not Turbo, not
   color) gave the best performance on a Pi 4.
4. **Boot Options**: set Boot device to `SCSI disk`; uncheck both
   `SCSI tests` and `Verbose test mode`.
5. **SCSI Disks**: add your NeXTSTEP disk image as `SCSI Disk 0`.
6. Click **Save config** (not just OK) to persist these to
   `~/.config/previous/previous.cfg`.
7. NeXTSTEP will pause waiting for a network config server (Ethernet
   isn't emulated) - press **Ctrl-C** to continue booting past that.
8. To shut down cleanly from inside NeXTSTEP, press **F10** (not a
   guest-OS shutdown menu item).

**Gotcha confirmed on real hardware (2026-09-23):** unchecking "Show at
startup" in the GUI and clicking Save config does *not* reliably persist
that one setting - the config dialog kept reopening on every launch
regardless. Previous has no command-line flag to suppress it either (the
man page is explicit: no CLI flags at all). Fix it directly in the saved
config file instead:

```
sed -i 's/^bShowConfigDialogAtStartup = TRUE/bShowConfigDialogAtStartup = FALSE/' ~/.config/previous/previous.cfg
```

After that, `previous.cfg` remembers everything (machine type, boot
options, disk path) and later launches from the picker boot straight
into NeXTSTEP with no dialog and no F12 needed - only the disk path
changes if you move the `.dd`/image file.

A separate, unexplained wrinkle also showed up during initial setup on a
Pi 4: launching `/usr/bin/previous` directly from the picker (via
`subprocess.run`, no wrapper) reliably exited after almost exactly 3
seconds *before* `previous.cfg` existed at all, with no crash/error in
its output - reproducible standalone via SSH too regardless of
`start_new_session`/env vars, but never once it had a saved config to
load. Once `previous.cfg` exists (from the one-time setup above),
launching it directly is stable. If this ever recurs on a fresh Pi,
deleting `~/.config/previous/` and redoing the one-time setup is the
known trigger to watch for, not something to chase as a launcher bug
first.

## 7. LinApple (Apple II / II+ / //e)

Installed from a pre-built `.deb` (github.com/linappleii/linapple
releases, an actively-maintained project - not the older abandoned
"linapple-pie" fork, whose changes have been merged upstream here):

```
curl -LO https://github.com/linappleii/linapple/releases/download/v3.0-beta-3/linapple-v3.0-beta-3-linux-arm64.deb
sudo apt-get install -y ./linapple-v3.0-beta-3-linux-arm64.deb
```

**Bundles its own Apple II ROMs** (built in, not separate files) - no
ROM sourcing needed at all, unlike every other emulator in this project.

### Two packaging gotchas on arm64/trixie (both confirmed 2026-09-23)

This is a beta release and its arm64 `.deb` has real packaging bugs on
current Debian trixie - both needed a manual fix after `apt-get install`
otherwise succeeded:

1. **`libSDL3_image.so.0` isn't even declared as a dependency**, despite
   the binary needing it. Install it separately:
   ```
   sudo apt-get install -y libsdl3-image0
   ```
2. **The binary is linked against `libzip.so.4`, which doesn't exist on
   trixie** (renamed to `libzip.so.5` - the `.deb`'s declared
   `libzip4 | libzip-dev` dependency lets `apt` install `libzip-dev`
   instead, which satisfies the *packaging* dependency check but not the
   actual *runtime* linker, since `libzip-dev` doesn't ship the old
   soname either). A compatibility symlink fixes it - libzip's C API
   (`zip_open`/`zip_fopen`/`zip_fread`/etc.) has stayed stable across its
   soname bumps for years, so this is low-risk despite looking hacky:
   ```
   sudo ln -sf /usr/lib/aarch64-linux-gnu/libzip.so.5.5 /usr/lib/aarch64-linux-gnu/libzip.so.4
   sudo ldconfig
   ```

Verify both are fixed with `ldd /usr/bin/linapple | grep "not found"` -
it should print nothing.

### Total Replay (a ready-to-boot game library)

[Total Replay](https://archive.org/details/TotalReplay) is a single
ProDOS hard-disk image (`.hdv`) bundling hundreds of native Apple II
games behind a menu - much more convenient for a kiosk than sourcing
individual floppy images:

```
curl -L -o ~/TotalReplay_v6.1.hdv "https://archive.org/download/TotalReplay/Total%20Replay%20v6.1.hdv"
```

`config.json`'s `apple2` entry launches straight into it via
`linapple-run-with-led.sh` (§2's LED wrapper), forwarding all arguments
to the real binary:
```
["/home/wottle/lisa-mini-pi/software/lisa-pi-launcher/linapple-run-with-led.sh", "--hd1", "/home/wottle/TotalReplay_v6.1.hdv", "--autoboot", "--fullscreen"]
```

`linapple --help` lists the full flag set if you want a different boot
disk/hard disk instead - `-1`/`-2` for floppy drives 1/2, `--hd1`/`--hd2`
for hard disks (Slot 7), `-a`/`--autoboot`, `-f`/`--fullscreen`.

## 8. Custom boot splash

Raspberry Pi OS's boot splash (the image shown between the rainbow-square
firmware screen and the kiosk actually starting) is Plymouth, using the
stock `pix` theme. That theme's script
(`/usr/share/plymouth/themes/pix/pix.script`) auto-scales and centers
whatever `splash.png` it finds in its own theme directory to fit the
actual connected display — so `software/boot-splash/splash.png` doesn't
need to exactly match any particular panel's resolution, just its
approximate aspect ratio (it's 1448x1086, 4:3, matching the 1024x768
target panel).

```
sudo software/boot-splash/install.sh
sudo reboot
```

The script backs up the stock image to
`/usr/share/plymouth/themes/pix/splash.png.orig` (once — it won't
overwrite an existing backup) before installing the custom one, and runs
`update-initramfs -u` afterward, which is required on current Raspberry
Pi OS (`auto_initramfs=1` in `/boot/firmware/config.txt`) — Plymouth
reads its theme files out of the initramfs image at early boot, not
directly off the live root filesystem, so a plain file copy alone
doesn't take effect until the initramfs is rebuilt.

It also idempotently adds `splash`, `quiet`, and
`plymouth.ignore-serial-consoles` to `/boot/firmware/cmdline.txt` if
they're missing — confirmed on real hardware (2026-09-27) that without
`splash`/`quiet`, Plymouth never engages at all and boot just shows raw
kernel/systemd text instead of this image, and separately that Plymouth
disables its graphical splash whenever it detects a serial console
(`console=serial0,115200`, part of this cmdline by default), which is a
sensible default for a headless Pi but wrong for this kiosk.

To revert to the stock Raspberry Pi splash:

```
sudo cp /usr/share/plymouth/themes/pix/splash.png.orig /usr/share/plymouth/themes/pix/splash.png
sudo update-initramfs -u
```

### Disabling the rainbow firmware splash

Before Plymouth (or even Linux) starts, the Pi's GPU firmware briefly
shows a rainbow-square diagnostic test pattern. That screen is rendered
directly by the firmware, not from an image file, so there's no supported
way to replace it with custom art — only to skip it. Add this to
`/boot/firmware/config.txt`, in the global section above the
`[cm4]`/`[cm5]`/`[pi5]` platform-specific sections (e.g. right after
`arm_boost=1`):

```
disable_splash=1
```

With it set, boot goes straight from a brief black screen into the
Plymouth splash above instead of showing the rainbow test pattern first.

## 9. Display mode and performance (Pi 5 + iPad 3/4 panel)

Findings from a diagnosis session on 2026-11-21: a Raspberry Pi 5 (4 GB,
Debian 13, kernel 6.18) driving an iPad 3/4 panel (2048x1536 native)
through an HDMI controller board (make/model not recorded). Everything
below was measured on that one build unless marked otherwise.

**Display mode.** The Pi is driven at **1024x768@60**, not the panel's
native 2048x1536, and the controller board upscales it (the panel's EDID
lists 1024x768 at 60 and 75 Hz). `system/xsession-launcher.sh` does this
with `xrandr` before the launcher starts. Reasons: every emulator here is
set up for 1024x768 (so they render 1:1, with no software scaling) and the
Pi pushes a quarter of the pixels. I judged the picture good by
eye; edge cropping and sharpness against native were not recorded
separately. The console and boot splash still appear at the native mode.
To use native instead, run `scripts/display-mode.sh native` and restart
the kiosk (`display-mode.sh 1024` goes back; `status` shows what is set).

**Ruled out as the cause of slowness:** throttling or undervoltage
(`get_throttled` = `0x0` throughout, 47-57 °C), the CPU clock (1.9 GHz idle,
2.4 GHz within seconds of load under `ondemand`), the HDMI mode, GPU
acceleration (glamor on V3D; Basilisk II uses the OpenGL renderer) and the
SD card (93 MB/s sequential, 0.3 ms random 4 KB reads).

**Fixed:**

| Problem | Cause | Fix |
|---|---|---|
| Launcher didn't fill the 2048x1536 screen | fixed 1024x768 layout | `theme.apply_scale()` (whole-number scale, centred); a no-op at 1024x768 |
| Launcher ~48.5% of a core when idle | full-frame redraw 30x/s | `redraw.py`: repaint only on change (~2-3% idle) |
| Basilisk II mouse and drawing jerky | `frameskip` default 0 = ~11 updates/s | `frameskip 1` = ~61/s (0, 1 and 6 tried) |
| LisaEm showed 1/4 of the screen | `hidpi_scale=200` in `~/.lisaem` | `hidpi_scale=100` at a 1024x768 output |
| LisaEm picture pushed down 43 px and clipped, pointer "escapes" at the edges (intermittent, ~half of launches) | centred from the frame rectangle (sometimes 815 px tall); mouse released in the margins | local patch to `lisaem_wx.cpp`: centre from the client area, clamp the pointer in Fill mode (see SETUP.md Known gaps) |

The Basilisk II rate was measured with an `LD_PRELOAD` shim counting
`SDL_RenderPresent` calls per second while injected mouse motion circled
on the guest, on a scratch copy of the disk image. The software renderer,
`sdl_vsync false`, `idlewait true` and `screen win/1024/768` all stayed at
~11/s.

**My impressions after the changes:** Basilisk II "looked great",
Mini vMac "seems better", Previous "working well", LisaEm "looks great".
LinApple was not checked. These are impressions, not benchmark scores.

**Not verified:** the controller board's scaling quality; sustained load
or temperature with the case closed; the 5 V supply under heavy load; a
Pi 4 at this mode; the Apple II emulator; the kernel `video=` route; and
Speedometer scores (one run under synthetic mouse input left the guest
unresponsive for over a minute, cause unknown - possibly the harness).

**Native-resolution trial (2026-11-21).** Basilisk II with `frameskip 1`
at the panel's native 2048x1536 held ~60 screen updates/s (measured, same
method as above) in all three of: the default 2x upscale, `scale_nearest
true` + `scale_integer true` (crisp pixel doubling; looks like the 1024x768
layout at twice the size) and a guest running at native size
(`screen dga/2048/1536`; very small UI, lots of workspace, some 33 ms
gaps). The default upscale looked slightly soft. So the slowness was never
the resolution. `display-mode.sh native` sets up the crisp variant. **Outcome:
I tried native on the panel and went back to 1024x768** - the UI
is too small at native resolution. Also seen: Mini vMac (a fixed 1024x684
build) showed as a small centred window; and LisaEm's "Fill 1024x768" mode
(`vidmod_fill1024`) draws a 1024x728 bitmap scaled by `hidpi_scale`, i.e.
2048x1456 on the 1536-tall screen - measured 40 px margins above and below,
and the pointer stops controlling the Lisa while it is in them (the source
only delivers the mouse while it is over the picture, `mouse_in_crt`). The
same code leaves 20 px margins at 1024x768 (the mouse there was not
tested). Previous and LinApple were not checked at native. Making native
usable would need a Mini vMac rebuild with `-mf 4` (not done). A LisaEm
patch that clamps the pointer to the picture edge and centres from the
client area was made for the 1024x768 case (see the table above); it was
not tested at native.
