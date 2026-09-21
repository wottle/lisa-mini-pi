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
software/lisa-pi-launcher/lisa-run-with-led.sh -p -d -F -q
```

(`-p -d -F -q`: power on immediately, boot from the ProFile/Widget drive,
fullscreen, quit the process once the Lisa powers off.)

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
