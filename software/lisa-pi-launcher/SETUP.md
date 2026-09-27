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

- Raspberry Pi 4 Model B (a Pi 5 also works the same way for everything
  in this file — same 64-bit Debian "trixie" OS image, same apt packages,
  same build steps. The one Pi-4-specific item in this repo is the
  `vc4_hvs` kernel warning noted in §7's Known Gaps for the desktop↔kiosk
  switch on a Pi 4 + this project's HDMI panel; that hasn't been tested
  on a Pi 5, since Pi 5 uses a different display driver stack).
- microSD card (boot media)
- The final target display is a 1024x768 HDMI LCD panel (a repurposed
  iPad 2 panel + HDMI driver board) — a Lisa-shaped 3D-printed case is
  built around it. Everything in this repo that's "sized for the real
  display" means 1024x768, even while testing on a different monitor.
- USB keyboard/mouse
- A second computer with [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
  installed and a microSD card reader (built-in or USB), to flash the card
  before it ever goes in the Pi.

## 1. Flash the OS

1. Insert the microSD card into your computer's reader and open Raspberry
   Pi Imager.
2. **Choose Device** → your Pi model (**Raspberry Pi 4** or **Raspberry
   Pi 5**).
3. **Choose OS** → **Raspberry Pi OS (64-bit)** — this is in the top-level
   list, not under "Raspberry Pi OS (other)". Current release (Debian
   "trixie"-based as of this writing) — the **full Desktop image**, not
   Lite. (The kiosk itself doesn't need a desktop environment — see §5 —
   but Basilisk II's apt package and this guide's dependencies assume the
   full image's repositories/desktop-adjacent packages are available.
   Lite hasn't been tested with this setup.)
4. **Choose Storage** → your microSD card. Double-check you've picked the
   card and not another drive — this step erases whatever's selected.
5. Click **Next**. The Imager will ask "Would you like to apply
   OS customisation settings?" — click **Edit Settings** (this is the
   gear-icon/Ctrl-Shift-X panel from older Imager versions, just presented
   as a prompt now). Set, across its **General** and **Services** tabs:
   - **General tab**: hostname (e.g. `lisa-pi.local`), username/password,
     Wi-Fi SSID/password if the Pi won't be on Ethernet, locale/timezone/
     keyboard layout.
   - **Services tab**: toggle **Enable SSH** on, then choose either
     "Use password authentication" or "Allow public-key authentication
     only" (paste your public key if so). Password auth is simplest for
     a first-time setup; switch to key-only later if you want.
   - Click **Save**, then confirm you want to apply these settings when
     prompted.
6. Click **Yes** to begin writing, then **Yes** again to confirm erasing
   the card. Wait for the write + verify to finish (a few minutes).
7. Move the card to the Pi, connect Ethernet or rely on the Wi-Fi
   credentials set above, and power it on. First boot (partition resize,
   first-run services) can take a minute or two longer than later boots —
   give it 2-3 minutes with no keyboard/monitor needed before trying to
   connect.
8. SSH in from your computer. SSH is just a way to type commands on the
   Pi from your computer's own keyboard, over the network, instead of
   plugging a keyboard/monitor into the Pi directly. Steps below are for
   macOS (Windows: use the similarly-named "Terminal" app or PowerShell,
   same `ssh` command; Linux: same as macOS).
   1. Open the **Terminal** app: press **Cmd+Space**, type `Terminal`,
      press **Return**.
   2. Type this, replacing `<user>` with the username you set in step 5
      and `<hostname>` with the hostname you set in step 5 (e.g. if you
      used username `pi` and hostname `lisa-pi`, type exactly
      `ssh pi@lisa-pi.local`), then press **Return**:
      ```
      ssh <user>@<hostname>.local
      ```
   3. The first time you connect to any new device, Terminal will show a
      warning like `The authenticity of host ... can't be established`
      and ask `Are you sure you want to continue connecting?`. This is
      expected — type `yes` and press **Return**. You won't see this
      warning again for this Pi.
   4. It will then ask for the password you set in step 5. Type it and
      press **Return** — **nothing will appear on screen as you type**,
      not even dots. That's normal terminal behavior, not a bug; just
      type the full password and hit Return.
   5. Success looks like your prompt changing to something like
      `<user>@<hostname>:~ $` — you're now typing commands on the Pi
      itself. Every command in the rest of this guide runs here, not on
      your own computer.
   - **If it hangs or says `Could not resolve hostname` / `Operation timed
     out`**: the Pi is probably still booting, or `.local` name lookup
     isn't working on your network. Wait another minute and retry the
     same command. If it still fails after a few tries, find the Pi's IP
     address instead — check your Wi-Fi router's admin page for a list of
     connected devices (look for the hostname you set), then use that
     numeric address in place of `<hostname>.local`, e.g.
     `ssh pi@192.168.1.42`.

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
(`https://github.com/wottle/lisaem`), branch **`lisa-fixes-1024x768`**,
which has a real upstream Linux/ARM portability fix (`typedef char sint8`
is unsigned on Linux/ARM but signed on macOS/x86, breaking every backward
branch displacement in the 68k core — fixed to `typedef signed char
sint8`), several UX enhancements (kiosk `-k` flag, hotkeys, Fill/Fit
display modes), and the F12 power-button hotkey that the GPIO power
button/LED watcher (`docs/software-setup.md` §2) depends on. Don't build
the unmodified upstream `arcanebyte/lisaem`, and don't omit the branch —
this fork's default branch doesn't have these fixes.

```
git clone --branch lisa-fixes-1024x768 https://github.com/wottle/lisaem.git ~/lisaem-fixes-src
```

LisaEm needs wxWidgets 3.2.1 built from source (Debian's packaged wx is
typically older/incompatible). This also needs `libgtk-3-dev` — GTK's
development headers, not just the runtime libraries already on the
system — which isn't installed by §2's base-package list above; without
it, `configure --with-gtk` below fails to find GTK at all:

```
sudo apt install -y libgtk-3-dev
```

Then build wxWidgets itself into `/usr/local/wx3.2.1-gtk`
(`/usr/local/wx3.2.1-gtk/bin` must be on `PATH` before building LisaEm):

```
mkdir -p ~/wx-build
cd ~/wx-build
curl -L https://github.com/wxWidgets/wxWidgets/releases/download/v3.2.1/wxWidgets-3.2.1.tar.bz2 \
  -o wxWidgets-3.2.1.tar.bz2
tar xjf wxWidgets-3.2.1.tar.bz2
cd wxWidgets-3.2.1
mkdir build-gtk
cd build-gtk
CFLAGS="-fPIC" CXXFLAGS="-fPIC" ../configure \
  --with-gtk --enable-unicode --disable-debug --disable-shared \
  --without-expat --disable-richtext \
  --with-libpng=builtin --with-libjpeg=builtin --with-libtiff=builtin --with-libxpm=builtin \
  --prefix=/usr/local/wx3.2.1-gtk
make -j"$(nproc)"
sudo make install
```

This step alone can take a while (dozens of minutes depending on the
Pi) — it's compiling all of wxWidgets from source. Then build LisaEm
itself:

```
export PATH=/usr/local/wx3.2.1-gtk/bin:$PATH
cd ~/lisaem-fixes-src
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

**Confirmed-working asset note (2026-09-26):** the disk image must be a
bootable ProFile/Widget hard-disk `.dc42` image, matched to the `-d`
(boot hard disk) flag `lisa-run-with-led.sh` passes — a set of individual
LOS installer floppy `.image` files (e.g. one named like `LOS 3.1
1.image` through `5.image`) is **not** a substitute; those would need an
actual from-floppy OS install onto a blank hard-disk image first, which
this guide doesn't cover. If copying assets from a Mac, from a **second,
separate Terminal window on the Mac** (not the Pi's SSH session — `scp`
pushes from local to remote):
```
scp /path/to/boot.ROM <user>@<pi-hostname>.local:~/boot.ROM
scp /path/to/lisaem-widget.dc42 <user>@<pi-hostname>.local:~/lisaem-widget.dc42
```

**Placing the files is not enough — LisaEm doesn't auto-discover
`~/boot.ROM`/`~/lisaem-widget.dc42` by filename convention.** After first
run, `~/lisaem.conf` exists with `ROMFILE=` empty and
`[parallelport] path=lisaem-profile.dc42` (LisaEm's own compiled-in
default, which won't exist on your Pi). You must point these at your
actual files — trying to boot before doing this shows LisaEm's default
skin UI with a "no ROM" warning instead of powering on:
```
sed -i 's|^ROMFILE=.*|ROMFILE=/home/<user>/boot.ROM|' ~/lisaem.conf
sed -i 's|^path=lisaem-profile.dc42|path=/home/<user>/lisaem-widget.dc42|' ~/lisaem.conf
```

**If an *existing/pre-installed* Lisa Office System disk image fails to
boot with `Error 10738`** ("Checksum failure or too many hardware config
changes" — a genuine Lisa OS error, see
`~/lisaem-fixes-src/src/lisa/motherboard/los-error-codes.c`), the disk
image was "married" to a different hardware identity than this LisaEm
instance's default one. `~/lisaem.conf`'s freshly-created `serialnumber=`
and `[pram]` block are just placeholders (`ff000000...`, all-zero PRAM) —
if the disk was previously used with a different LisaEm/real Lisa, its
OS remembers *that* identity and rejects a mismatched one. Fix by copying
the exact `serialnumber=` line and `[pram]` block from whatever
LisaEm instance the disk image already boots successfully on into this
Pi's `~/lisaem.conf` (leave `ROMFILE`/`[parallelport] path` as your
Pi-local paths — only `serialnumber` and `[pram]` need to match). This
only applies to reusing an already-installed disk image; a truly blank
image installed fresh from floppies establishes its own identity on
first boot and won't hit this.

**Confirmed real bug (2026-09-26) in this fork's `-k` flag: it doesn't
actually turn off LisaEm's skin UI**, despite the docs above describing
`-k` as fullscreen+skinless+power-on+quit-on-shutdown. Root cause, in
`~/lisaem-fixes-src/src/host/wxui/lisaem_wx.cpp`: `wxCmdLineSwitchState`
is `OFF=-1, NOT_FOUND=0, ON=1` (see
`/usr/local/wx3.2.1-gtk/include/wx-3.2/wx/cmdline.h`), but `-k`'s handler
(line ~3564) sets `on_start_skin = 0;` — the *NOT_FOUND* sentinel, not
`wxCMD_SWITCH_OFF` (-1) — so the downstream `if (on_start_skin ==
wxCMD_SWITCH_OFF)` check (line ~3468) never fires and the skin setting
just falls through to whatever `~/.lisaem` has saved. (The fullscreen
half of `-k` sets `on_start_fullscreen = 1`, which correctly matches
`wxCMD_SWITCH_ON` — only the skin toggle is affected.) Not yet patched
upstream in the fork. **Workaround**: write these known-working values
directly into `~/.lisaem` (confirmed on real hardware, both Pi 4 and Pi
5) rather than relying on `-k` to set them:
```
cat > ~/.lisaem <<'EOF'
hidpi_scale=100
soundeffects=1
displayskins=0
displaymode=6
centerskinless=1
asciikeyboard=1
lisaconfigfile=/home/<user>/lisaem.conf
throttle=16
emutime=40
emutick=25
hostrefreshrate=0
forcerefresh=0
use_mouse_scale=0
hidehostmouse=1
disable_screen_dimming=1
mousetopmenufullscreen=0
[lisawin]
sizey=768
sizex=1024
[lisaframe]
sizey=768
sizex=1024
fullscreen=1
[lisaskin]
name=default
EOF
```
(`displayskins=0` + `displaymode=6` is the skinless "Fill" video mode
that fills the real 1024x768 panel; `throttle=16`/`hidehostmouse=1`/
`disable_screen_dimming=1` are the project's own tuned values for a
dedicated kiosk display, not required just to fix the skin issue.)

## 4. Basilisk II

Already installed via apt (§2). You need a 68k Mac ROM and a classic Mac
OS disk image — these aren't redistributed here. Place them and edit
`~/.config/BasiliskII/prefs` (created on first run) to point at them.
**Confirmed-working filenames (2026-09-26):** a Mac LC III ROM as
`mac-lciii.rom` and a System 7.5.3 disk image as `macos753.image` — any
68k ROM/disk image works in principle, but these are the exact names this
example config below assumes. From a **second, separate Terminal window
on your Mac** (not the Pi's SSH session):
```
scp /path/to/your-mac-rom.rom <user>@<pi-hostname>.local:~/mac-lciii.rom
scp /path/to/your-macos-disk.image <user>@<pi-hostname>.local:~/macos753.image
```

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

**Expected, harmless noise:** `bash setup.sh` prints
`setup.sh: line 520: -Icfg/: No such file or directory` (line number may
vary) partway through. Confirmed (2026-09-26, Pi 5) that this doesn't
stop `setup.sh` from finishing or writing a usable Makefile — `make`
right after picks up the `sed`-patched include paths correctly and
produces a working `minivmac` binary. Don't stop and troubleshoot this
line on its own; only worry if `make` itself fails afterward.

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
them. **Confirmed-working filenames (2026-09-26):** `MacII.ROM` and a
partitioned hard-disk image named `System6.image` (a real System 6.0.8
HD image, not a plain floppy image):

```
mkdir -p ~/minivmac-final
cp ~/minivmac-erich/minivmac ~/minivmac-final/minivmac
```

Then, from a **second, separate Terminal window on your Mac** (not the
Pi's SSH session — `scp` pushes from local to remote):
```
scp /path/to/your-mac-ii.rom <user>@<pi-hostname>.local:~/minivmac-final/MacII.ROM
scp /path/to/your-system6.image <user>@<pi-hostname>.local:~/minivmac-final/System6.image
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

Rather than hand-editing XML, this script (idempotent — safe to re-run,
won't duplicate the rule) does the insertion for you:

```
python3 - <<'PYEOF'
import pathlib
path = pathlib.Path.home() / ".config/openbox/rc.xml"
text = path.read_text()
rule = '  <application class="*">\n    <decor>no</decor>\n  </application>\n'
if 'class="*"' not in text:
    text = text.replace("</applications>", rule + "</applications>")
    path.write_text(text)
    print("Rule inserted.")
else:
    print("Rule already present, skipped.")
PYEOF
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

- ~~**§3's LisaEm build instructions are for the wrong fork/branch on at
  least one real Pi.**~~ **CLOSED (2026-09-26).** §3 now clones
  `--branch lisa-fixes-1024x768` into `~/lisaem-fixes-src`, matching what
  `lisa-run-with-led.sh` actually hardcodes as `LISAEM_BIN`
  (`$HOME/lisaem-fixes-src/bin/lisaem`) and what `docs/software-setup.md`
  and `provision.sh` already used — the old `~/lisaem`/no-branch clone
  would have built a binary the launcher could never find. This section
  previously also flagged a missing `-M`/`-M-` flag on this branch for
  keeping Shut Down mouse-reachable — `docs/software-setup.md` §2 already
  documents that this was fixed by patching the branch's `-k` flag to
  leave the mouse-to-top-menu setting at its saved default instead of
  forcing it off, so no CLI flag is needed; not re-verified independently
  in this pass.
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
