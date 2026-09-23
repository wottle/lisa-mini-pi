# Software Setup

End-to-end setup for the software side of the Lisa Mini Pi: the patched
LisaEm build, the kiosk launcher, the physical power-button/LED wiring, and
the boot-time systemd configuration that ties it all together.

Basilisk II and Mini vMac sections are stubs — installation steps for those
still need to be documented.

## 1. Apple Lisa emulation: building the patched LisaEm

The stock `arcanebyte/lisaem` has a couple of Linux/ARM-specific bugs.
`wottle/lisaem` (branch `lisa-fixes-1024x768`) carries the fixes on top of
`arcanebyte/lisaem`'s `master`, including:

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
git clone --branch lisa-fixes-1024x768 https://github.com/wottle/lisaem.git ~/lisaem-fixes-src
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

## 2. GPIO power button and LED

Hardware wiring:

- **LED** (status/power indicator): GPIO18, driven directly as an output.
- **Power button switch**: 3.3V → resistor (~1kΩ) → switch → GPIO17,
  configured as an input with the internal pull-down enabled, so it reads
  a clean low when open and high when the switch closes.

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

**`-k` on the `lisa-fixes-1024x768` branch used to unconditionally force
mouse-to-top-reveals-menu off** - fine for a picker with no other UI, but
on a kiosk with no titlebar/window-manager chrome, that's the *only* way
to reach the Special/Shut Down menu without a keyboard, so it's been
patched to leave that setting at its saved default (on) instead. There's
no `-M`/`-M-` flag on this branch to fix it via the command line the way
the other `wottle/lisaem` branch used - see the patch note in
`software/lisa-pi-launcher/SETUP.md`'s Known Gaps if rebuilding from a
clean checkout of this branch.

### `lisa-power-button-watcher.sh`

A **persistent** watcher — meant to run for the entire time the Pi is on,
independent of whether the launcher menu or LisaEm is currently showing
(started once, alongside `openbox`, in `system/xsession-launcher.sh`; see
below). On each GPIO17 press:

- If LisaEm is already running, it sends it F12 (shuts it down).
- If LisaEm is not running, it launches it via `lisa-run-with-led.sh`
  instead — the button "powers on" the Lisa.

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
  `launcher.py` (see `system/xsession-launcher.sh`).
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

## 4. Basilisk II (classic Mac OS, System 7.5.3)

TODO: document install/configuration steps. Currently installed at
`/usr/bin/BasiliskII`, launched by the launcher with no extra flags — see
`config.json`.

## 5. Mini vMac (classic Mac OS, System 6.0.8)

TODO: document install/configuration steps. Currently installed at
`~/minivmac-final/`, launched by the launcher with a specific ROM and
System 6 disk image — see `config.json`.

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
subsequent launch - so `config.json`'s `next` entry is just
`["/usr/bin/previous"]` with nothing else, and the one-time interactive
setup below has to happen at the physical Pi (keyboard required for a
couple of steps).

You'll need a NeXTSTEP disk image - not redistributed here. One-time
setup, at the Pi, with a keyboard attached:

1. Launch Previous from the picker (or run `/usr/bin/previous` directly
   for this first-run setup). The settings GUI opens automatically on
   first launch.
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

`config.json`'s `apple2` entry launches straight into it:
```
["/usr/bin/linapple", "--hd1", "/home/wottle/TotalReplay_v6.1.hdv", "--autoboot", "--fullscreen"]
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
