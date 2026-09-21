# Lisa Boot Launcher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fullscreen pygame kiosk app that shows an authentic-looking
Apple Lisa hardware-diagnostic-styled boot screen, then lets the user pick a
vintage-computer emulator (initially just LisaEm) with arrow keys + Enter,
launches it, and returns to the picker when it exits.

**Architecture:** Pure-logic modules (config loading, boot-diagnostic timer,
selection state machine, bitmap font) are unit-tested headlessly with
pygame's `dummy` video driver. A `rendering` module composes those into
pixel output on a low-resolution (512x384) surface using only the hand-rolled
font and procedurally-generated 1-bit icons, nearest-neighbor-scaled up to
the real 1024x768 screen. `launcher.py` is the thin main-loop/event-handling
entry point tying it together; it and the systemd/X11/polkit integration are
verified manually on real Pi hardware, since there's no meaningful headless
test for a fullscreen kiosk's actual on-screen behavior or OS integration.

**Tech Stack:** Python 3, pygame (rendering/input/subprocess control),
Pillow (one-time procedural icon generation), pytest (unit tests),
systemd (autostart/respawn), minimal X11 session (xinit, no window manager
chrome).

**Spec:** `/Users/wottle/Documents/Development/lisa-pi-launcher/docs/superpowers/specs/2026-09-16-lisa-boot-launcher-design.md`

## Global Constraints

- Pure 1-bit black/white rendering everywhere practical — no antialiasing,
  no gradients, no transparency, no color, no rounded rects, no glow/shadow
  effects beyond the one hard-edged drop-shadow described below.
- No modern fonts or system fonts — text is drawn from a hand-rolled bitmap
  font, never `pygame.font`/TTF.
  no easing/tweening on any animation (boot diagnostic sweep, blink) — hard
  cuts between states only.
- Selection is always shown as full reverse video (solid black fill, white
  content) — never a border, glow, checkmark, or color highlight.
- All layout numbers live in `theme.py` as named constants — no magic
  numbers scattered through rendering/app code.
- Logical render surface is 512x384; final output is 1024x768 via
  nearest-neighbor scaling only (`pygame.transform.scale`, never
  `smoothscale`).
- `command` in `config.json` is a plain argv list, never a shell string.
- Keyboard (Left/Right/Enter/S/R) is the primary input; mouse support is
  not required for v1.

---

## Task 1: Project scaffolding, theme constants, and config loader

**Files:**
- Create: `requirements.txt`
- Create: `theme.py`
- Create: `config.py`
- Create: `config.json`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `theme.SCREEN_WIDTH: int`, `theme.SCREEN_HEIGHT: int`,
  `theme.LOGICAL_WIDTH: int`, `theme.LOGICAL_HEIGHT: int`,
  `theme.PANEL_X: int`, `theme.PANEL_Y: int`, `theme.PANEL_WIDTH: int`,
  `theme.PANEL_HEIGHT: int`, `theme.SHADOW_OFFSET: int`,
  `theme.ICON_SIZE: int`, `theme.ICON_SPACING: int`, `theme.FONT_SCALE: int`,
  `theme.TOP_STRIP_HEIGHT: int`, `theme.BOOT_DIAG_STEP_SECONDS: float`
- Produces: `config.SystemEntry` (dataclass: `id: str`, `name: str`,
  `subtitle: str`, `icon: str`, `command: list[str]`),
  `config.load_config(path: str) -> list[SystemEntry]` (raises `ValueError`
  on missing/malformed fields)

- [ ] **Step 1: Create the project's Python dependency list**

`requirements.txt`:
```
pygame>=2.5
Pillow>=10.0
pytest>=7.0
```

- [ ] **Step 2: Create the theme/layout constants module**

`theme.py`:
```python
"""Centralized layout constants for the Lisa boot launcher.

Every pixel position/size used anywhere in rendering.py or launcher.py
must come from here - no magic numbers elsewhere.
"""

# Real output resolution (the physical panel)
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768

# Logical render resolution - everything is drawn here, then
# nearest-neighbor scaled up to SCREEN_WIDTH x SCREEN_HEIGHT.
LOGICAL_WIDTH = 512
LOGICAL_HEIGHT = 384

# Thin white strip across the very top of the logical surface.
TOP_STRIP_HEIGHT = 6

# The white diagnostic/selection panel.
PANEL_X = 32
PANEL_Y = 24
PANEL_WIDTH = 448
PANEL_HEIGHT = 80
SHADOW_OFFSET = 3  # black drop-shadow offset, down and to the right

# Item (icon + label + status) layout inside the panel.
ICON_SIZE = 20          # icons are square, ICON_SIZE x ICON_SIZE logical px
ICON_SPACING = 96       # horizontal distance between item centers
ITEMS_TOP_MARGIN = 28   # vertical offset from panel top to the icon row

# Bitmap font scale: 1 logical pixel per font pixel (the font itself is
# already small - 5x7 - so no additional scale is applied at the logical
# resolution; the 2x logical->real scale-up is what makes it look
# authentically chunky on the real screen).
FONT_SCALE = 1

# Boot diagnostic animation timing.
BOOT_DIAG_STEP_SECONDS = 0.35
```

- [ ] **Step 3: Write the failing config loader test**

`tests/test_config.py`:
```python
import json
import pytest
from config import SystemEntry, load_config


def test_load_config_returns_system_entries(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "systems": [
            {
                "id": "lisa",
                "name": "LISA",
                "subtitle": "OFFICE SYSTEM 3.1",
                "icon": "icons/lisa.png",
                "command": ["/bin/echo", "lisa"]
            }
        ]
    }))

    systems = load_config(str(config_path))

    assert systems == [
        SystemEntry(
            id="lisa",
            name="LISA",
            subtitle="OFFICE SYSTEM 3.1",
            icon="icons/lisa.png",
            command=["/bin/echo", "lisa"],
        )
    ]


def test_load_config_rejects_missing_field(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "systems": [{"id": "lisa", "name": "LISA"}]
    }))

    with pytest.raises(ValueError):
        load_config(str(config_path))


def test_load_config_rejects_non_list_command(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "systems": [{
            "id": "lisa",
            "name": "LISA",
            "subtitle": "",
            "icon": "icons/lisa.png",
            "command": "not-a-list"
        }]
    }))

    with pytest.raises(ValueError):
        load_config(str(config_path))
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 5: Implement the config loader**

`config.py`:
```python
"""Loads and validates the launcher's system list from config.json."""

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class SystemEntry:
    id: str
    name: str
    subtitle: str
    icon: str
    command: list[str]


_REQUIRED_FIELDS = ("id", "name", "subtitle", "icon", "command")


def load_config(path: str) -> list[SystemEntry]:
    with open(path, "r") as f:
        data = json.load(f)

    systems_raw = data.get("systems")
    if not isinstance(systems_raw, list) or not systems_raw:
        raise ValueError(f"config.json at {path} has no non-empty 'systems' list")

    systems = []
    for entry in systems_raw:
        missing = [field for field in _REQUIRED_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"system entry {entry} missing fields: {missing}")
        if not isinstance(entry["command"], list):
            raise ValueError(f"system entry {entry['id']!r} 'command' must be a list, not a shell string")
        systems.append(SystemEntry(
            id=entry["id"],
            name=entry["name"],
            subtitle=entry["subtitle"],
            icon=entry["icon"],
            command=list(entry["command"]),
        ))
    return systems
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_config.py -v`
Expected: PASS (3 tests)

- [ ] **Step 7: Create the real config.json used by the app**

`config.json`:
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

- [ ] **Step 8: Commit**

```bash
git add requirements.txt theme.py config.py config.json tests/test_config.py
git commit -m "Add theme constants and config loader"
```

---

## Task 2: Hand-rolled bitmap font

**Files:**
- Create: `bitmap_font.py`
- Test: `tests/test_bitmap_font.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces: `bitmap_font.CHAR_WIDTH: int` (5), `bitmap_font.CHAR_HEIGHT: int`
  (7), `bitmap_font.text_size(text: str, scale: int = 1) -> tuple[int, int]`,
  `bitmap_font.render_text(surface: pygame.Surface, text: str, x: int, y:
  int, scale: int = 1, color: tuple[int, int, int] = (0, 0, 0)) ->
  pygame.Rect`

- [ ] **Step 1: Write the failing bitmap font tests**

`tests/test_bitmap_font.py`:
```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from bitmap_font import render_text, text_size, CHAR_WIDTH, CHAR_HEIGHT


def test_text_size_scales_with_character_count_and_scale():
    assert text_size("AB", scale=1) == (CHAR_WIDTH * 2 + 1, CHAR_HEIGHT)
    assert text_size("AB", scale=2) == ((CHAR_WIDTH * 2 + 1) * 2, CHAR_HEIGHT * 2)


def test_text_size_empty_string_is_zero():
    assert text_size("", scale=1) == (0, CHAR_HEIGHT)


def test_render_text_draws_black_pixels_on_white_surface():
    surface = pygame.Surface((64, 16))
    surface.fill((255, 255, 255))

    rect = render_text(surface, "A", 0, 0, scale=1, color=(0, 0, 0))

    assert rect.width == CHAR_WIDTH
    assert rect.height == CHAR_HEIGHT
    black_pixels = sum(
        1
        for px in range(rect.width)
        for py in range(rect.height)
        if surface.get_at((px, py))[:3] == (0, 0, 0)
    )
    assert black_pixels > 0


def test_render_text_unknown_character_renders_as_blank_cell():
    surface = pygame.Surface((64, 16))
    surface.fill((255, 255, 255))

    # '@' is not in the font table - should not raise, should occupy a
    # blank cell the width of one character.
    rect = render_text(surface, "@", 0, 0, scale=1, color=(0, 0, 0))

    assert rect.width == CHAR_WIDTH
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_bitmap_font.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'bitmap_font'`

- [ ] **Step 3: Implement the bitmap font**

`bitmap_font.py`:
```python
"""A hand-rolled 5x7 dot-matrix bitmap font.

Deliberately not pygame.font/TTF - this project's whole visual premise is
authentic hard-edged 1-bit Lisa-era text, and a real font renderer brings
antialiasing and modern glyph shapes we don't want. Each glyph is 7 rows of
a 5-bit mask (bit 4 = leftmost column, bit 0 = rightmost column).
"""

import pygame

CHAR_WIDTH = 5
CHAR_HEIGHT = 7
_CHAR_SPACING = 1

# fmt: off
FONT: dict[str, tuple[int, int, int, int, int, int, int]] = {
    "A": (0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "B": (0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110),
    "C": (0b01111, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b01111),
    "D": (0b11100, 0b10010, 0b10001, 0b10001, 0b10001, 0b10010, 0b11100),
    "E": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111),
    "F": (0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000),
    "G": (0b01111, 0b10000, 0b10000, 0b10011, 0b10001, 0b10001, 0b01111),
    "H": (0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001),
    "I": (0b01110, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "J": (0b00001, 0b00001, 0b00001, 0b00001, 0b10001, 0b10001, 0b01110),
    "K": (0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001),
    "L": (0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111),
    "M": (0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001),
    "N": (0b10001, 0b11001, 0b10101, 0b10101, 0b10011, 0b10001, 0b10001),
    "O": (0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "P": (0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000),
    "Q": (0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101),
    "R": (0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001),
    "S": (0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110),
    "T": (0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100),
    "U": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110),
    "V": (0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100),
    "W": (0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b10101, 0b01010),
    "X": (0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001),
    "Y": (0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100),
    "Z": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111),
    "0": (0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110),
    "1": (0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110),
    "2": (0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111),
    "3": (0b11111, 0b00010, 0b00100, 0b00010, 0b00001, 0b10001, 0b01110),
    "4": (0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010),
    "5": (0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110),
    "6": (0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110),
    "7": (0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000),
    "8": (0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110),
    "9": (0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100),
    " ": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000),
    ".": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b01100, 0b01100),
    ",": (0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000),
    "/": (0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000),
    ":": (0b00000, 0b01100, 0b01100, 0b00000, 0b01100, 0b01100, 0b00000),
    "-": (0b00000, 0b00000, 0b00000, 0b11111, 0b00000, 0b00000, 0b00000),
    "!": (0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100),
}
# fmt: on

_BLANK_GLYPH = (0, 0, 0, 0, 0, 0, 0)


def text_size(text: str, scale: int = 1) -> tuple[int, int]:
    if not text:
        return (0, CHAR_HEIGHT * scale)
    width = len(text) * CHAR_WIDTH + (len(text) - 1) * _CHAR_SPACING
    return (width * scale, CHAR_HEIGHT * scale)


def render_text(
    surface: pygame.Surface,
    text: str,
    x: int,
    y: int,
    scale: int = 1,
    color: tuple[int, int, int] = (0, 0, 0),
) -> pygame.Rect:
    cursor_x = x
    for ch in text.upper():
        glyph = FONT.get(ch, _BLANK_GLYPH)
        for row_index, row_bits in enumerate(glyph):
            for col_index in range(CHAR_WIDTH):
                bit = (row_bits >> (CHAR_WIDTH - 1 - col_index)) & 1
                if bit:
                    px = cursor_x + col_index * scale
                    py = y + row_index * scale
                    surface.fill(color, pygame.Rect(px, py, scale, scale))
        cursor_x += (CHAR_WIDTH + _CHAR_SPACING) * scale

    width, height = text_size(text, scale=scale)
    return pygame.Rect(x, y, width, height)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_bitmap_font.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add bitmap_font.py tests/test_bitmap_font.py
git commit -m "Add hand-rolled 5x7 bitmap font"
```

---

## Task 3: Boot diagnostic timer

**Files:**
- Create: `boot_diag.py`
- Test: `tests/test_boot_diag.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (takes its item list and step
  duration as plain constructor args; `launcher.py` will later pass
  `theme.BOOT_DIAG_STEP_SECONDS`)
- Produces: `boot_diag.BootDiagnostic` class with constructor
  `BootDiagnostic(items: list[str], step_seconds: float)`, method
  `update(dt: float) -> None`, property `done: bool`, property
  `current_index: int` (index of the item currently shown in reverse video,
  or `-1` once `done`), property `completed: set[int]` (indices whose
  diagnostic step has finished and should show a checkmark)

- [ ] **Step 1: Write the failing boot diagnostic tests**

`tests/test_boot_diag.py`:
```python
from boot_diag import BootDiagnostic


def test_starts_on_first_item_with_nothing_completed():
    diag = BootDiagnostic(items=["CPU", "MEM", "I/O", "DISK"], step_seconds=0.5)

    assert diag.current_index == 0
    assert diag.completed == set()
    assert diag.done is False


def test_advances_to_next_item_after_step_duration():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.5)

    assert diag.current_index == 1
    assert diag.completed == {0}
    assert diag.done is False


def test_partial_time_does_not_advance():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.3)

    assert diag.current_index == 0
    assert diag.completed == set()


def test_finishes_after_all_items_complete():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.5)
    diag.update(0.5)

    assert diag.done is True
    assert diag.current_index == -1
    assert diag.completed == {0, 1}


def test_accumulates_partial_updates_across_calls():
    diag = BootDiagnostic(items=["CPU", "MEM"], step_seconds=0.5)

    diag.update(0.3)
    diag.update(0.3)  # total 0.6s, past the 0.5s step boundary

    assert diag.current_index == 1
    assert diag.completed == {0}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_boot_diag.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'boot_diag'`

- [ ] **Step 3: Implement the boot diagnostic timer**

`boot_diag.py`:
```python
"""Drives the ~1-2 second boot-diagnostic animation before the picker
appears: a reverse-video highlight sweeps across a fixed list of items
(CPU / MEM / I/O / DISK), leaving a checkmark on each as it "completes"."""


class BootDiagnostic:
    def __init__(self, items: list[str], step_seconds: float):
        self._items = items
        self._step_seconds = step_seconds
        self._elapsed = 0.0
        self._completed: set[int] = set()

    def update(self, dt: float) -> None:
        if self.done:
            return
        self._elapsed += dt
        while (
            not self.done
            and self._elapsed >= self._step_seconds
        ):
            self._elapsed -= self._step_seconds
            self._completed.add(self._current_index_raw())

    def _current_index_raw(self) -> int:
        return len(self._completed)

    @property
    def done(self) -> bool:
        return len(self._completed) >= len(self._items)

    @property
    def current_index(self) -> int:
        if self.done:
            return -1
        return self._current_index_raw()

    @property
    def completed(self) -> set[int]:
        return set(self._completed)

    @property
    def items(self) -> list[str]:
        return list(self._items)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_boot_diag.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add boot_diag.py tests/test_boot_diag.py
git commit -m "Add boot diagnostic animation timer"
```

---

## Task 4: Selection state machine

**Files:**
- Create: `state.py`
- Test: `tests/test_state.py`

**Interfaces:**
- Consumes: `config.SystemEntry` (Task 1)
- Produces: `state.Phase` enum (`SELECTING`, `STARTING`),
  `state.LauncherState` class with constructor
  `LauncherState(systems: list[SystemEntry])`, method
  `move_selection(delta: int) -> None` (delta is `-1` or `+1`, clamps at
  the first/last system), property `selected_index: int`, property
  `selected: SystemEntry`, property `phase: Phase`, method
  `start_selected() -> None` (moves phase to `STARTING`), method
  `finish_starting() -> None` (moves phase back to `SELECTING`), method
  `panel_lines() -> tuple[str, str]` (the two lines of panel text for the
  current phase/selection)

- [ ] **Step 1: Write the failing state machine tests**

`tests/test_state.py`:
```python
import pytest
from config import SystemEntry
from state import LauncherState, Phase

LISA = SystemEntry(id="lisa", name="LISA", subtitle="OFFICE SYSTEM 3.1", icon="icons/lisa.png", command=["true"])
MAC = SystemEntry(id="mac", name="MACINTOSH", subtitle="SYSTEM 7.5.5", icon="icons/macintosh.png", command=["true"])


def test_starts_selecting_first_system():
    state = LauncherState([LISA, MAC])

    assert state.phase == Phase.SELECTING
    assert state.selected_index == 0
    assert state.selected == LISA


def test_move_selection_right_advances():
    state = LauncherState([LISA, MAC])

    state.move_selection(1)

    assert state.selected_index == 1
    assert state.selected == MAC


def test_move_selection_clamps_at_last_item():
    state = LauncherState([LISA, MAC])

    state.move_selection(1)
    state.move_selection(1)

    assert state.selected_index == 1


def test_move_selection_clamps_at_first_item():
    state = LauncherState([LISA, MAC])

    state.move_selection(-1)

    assert state.selected_index == 0


def test_start_selected_moves_to_starting_phase():
    state = LauncherState([LISA, MAC])

    state.start_selected()

    assert state.phase == Phase.STARTING


def test_finish_starting_returns_to_selecting():
    state = LauncherState([LISA, MAC])
    state.start_selected()

    state.finish_starting()

    assert state.phase == Phase.SELECTING


def test_panel_lines_while_selecting():
    state = LauncherState([LISA, MAC])

    assert state.panel_lines() == ("SELECT SYSTEM...", "LISA / OFFICE SYSTEM 3.1")


def test_panel_lines_while_starting():
    state = LauncherState([LISA, MAC])
    state.start_selected()

    assert state.panel_lines() == ("STARTING...", "STARTING LISA...")


def test_cannot_construct_with_empty_system_list():
    with pytest.raises(ValueError):
        LauncherState([])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'state'`

- [ ] **Step 3: Implement the state machine**

`state.py`:
```python
"""The selection state machine: which system is highlighted, and whether
we're idly selecting or currently launching one."""

from enum import Enum, auto

from config import SystemEntry


class Phase(Enum):
    SELECTING = auto()
    STARTING = auto()


class LauncherState:
    def __init__(self, systems: list[SystemEntry]):
        if not systems:
            raise ValueError("LauncherState requires at least one system")
        self._systems = systems
        self._selected_index = 0
        self._phase = Phase.SELECTING

    def move_selection(self, delta: int) -> None:
        new_index = self._selected_index + delta
        self._selected_index = max(0, min(len(self._systems) - 1, new_index))

    @property
    def selected_index(self) -> int:
        return self._selected_index

    @property
    def selected(self) -> SystemEntry:
        return self._systems[self._selected_index]

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def systems(self) -> list[SystemEntry]:
        return list(self._systems)

    def start_selected(self) -> None:
        self._phase = Phase.STARTING

    def finish_starting(self) -> None:
        self._phase = Phase.SELECTING

    def panel_lines(self) -> tuple[str, str]:
        if self._phase == Phase.STARTING:
            return ("STARTING...", f"STARTING {self.selected.name}...")
        return ("SELECT SYSTEM...", f"{self.selected.name} / {self.selected.subtitle}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_state.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add state.py tests/test_state.py
git commit -m "Add selection state machine"
```

---

## Task 5: Procedural icon generation

**Files:**
- Create: `gen_icons.py`
- Test: `tests/test_gen_icons.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (standalone script + importable
  drawing functions)
- Produces: `gen_icons.ICON_SIZE: int` (24), `gen_icons.draw_macintosh() ->
  PIL.Image.Image`, `gen_icons.draw_lisa() -> PIL.Image.Image`,
  `gen_icons.draw_next() -> PIL.Image.Image`, `gen_icons.draw_apple2() ->
  PIL.Image.Image`, `gen_icons.draw_ibmpc() -> PIL.Image.Image`,
  `gen_icons.draw_diag_cpu() -> PIL.Image.Image`,
  `gen_icons.draw_diag_mem() -> PIL.Image.Image`,
  `gen_icons.draw_diag_io() -> PIL.Image.Image`,
  `gen_icons.draw_diag_disk() -> PIL.Image.Image`, `gen_icons.main() ->
  None` (writes all of the above to `icons/*.png` as 1-bit images)

- [ ] **Step 1: Write the failing icon generation tests**

`tests/test_gen_icons.py`:
```python
from PIL import Image

from gen_icons import (
    ICON_SIZE,
    draw_macintosh,
    draw_lisa,
    draw_next,
    draw_apple2,
    draw_ibmpc,
    draw_diag_cpu,
    draw_diag_mem,
    draw_diag_io,
    draw_diag_disk,
)

ALL_DRAWERS = [
    draw_macintosh, draw_lisa, draw_next, draw_apple2, draw_ibmpc,
    draw_diag_cpu, draw_diag_mem, draw_diag_io, draw_diag_disk,
]


def test_every_icon_is_correct_size_and_mode():
    for drawer in ALL_DRAWERS:
        image = drawer()
        assert image.size == (ICON_SIZE, ICON_SIZE)
        assert image.mode == "1"


def test_every_icon_has_at_least_one_black_pixel():
    for drawer in ALL_DRAWERS:
        image = drawer()
        pixels = list(image.getdata())
        assert 0 in pixels, f"{drawer.__name__} produced an all-white icon"


def test_main_writes_all_icon_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import gen_icons

    gen_icons.main()

    expected_files = [
        "macintosh.png", "lisa.png", "next.png", "apple2.png", "ibmpc.png",
        "diag_cpu.png", "diag_mem.png", "diag_io.png", "diag_disk.png",
    ]
    for filename in expected_files:
        path = tmp_path / "icons" / filename
        assert path.exists(), f"missing {filename}"
        with Image.open(path) as img:
            assert img.size == (ICON_SIZE, ICON_SIZE)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_gen_icons.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'gen_icons'`

- [ ] **Step 3: Implement the icon generator**

`gen_icons.py`:
```python
"""Procedurally draws small 1-bit ROM-diagnostic-style icons and saves them
as PNGs under icons/. Run directly (`python3 gen_icons.py`) any time an
icon needs regenerating - this is a build-time tool, not part of the
running launcher.
"""

import os

from PIL import Image, ImageDraw

ICON_SIZE = 24
_BLACK = 0
_WHITE = 1


def _blank_canvas() -> Image.Image:
    image = Image.new("1", (ICON_SIZE, ICON_SIZE), _WHITE)
    return image


def draw_macintosh() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Compact-Mac silhouette: rounded body outline with a screen cutout
    # and a small base foot.
    draw.rectangle((4, 2, 19, 17), outline=_BLACK)
    draw.rectangle((7, 5, 16, 12), outline=_BLACK)  # screen
    draw.rectangle((2, 18, 21, 20), outline=_BLACK)  # base
    return image


def draw_lisa() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Boxier/wider than the Mac, with a second slot suggesting the twin
    # floppy/ProFile drives.
    draw.rectangle((2, 3, 21, 16), outline=_BLACK)
    draw.rectangle((4, 5, 12, 11), outline=_BLACK)  # screen
    draw.line((15, 6, 19, 6), fill=_BLACK)  # drive slot 1
    draw.line((15, 9, 19, 9), fill=_BLACK)  # drive slot 2
    draw.rectangle((0, 17, 23, 19), outline=_BLACK)  # base
    return image


def draw_next() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # NeXT was famously a solid black cube.
    draw.rectangle((5, 5, 18, 18), fill=_BLACK)
    return image


def draw_apple2() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Wide low keyboard body with a monitor perched on top, offset back.
    draw.rectangle((2, 14, 21, 20), outline=_BLACK)  # keyboard/body
    draw.rectangle((6, 3, 17, 13), outline=_BLACK)  # monitor
    draw.rectangle((8, 5, 15, 10), outline=_BLACK)  # screen
    return image


def draw_ibmpc() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # Separate rectangular system unit next to/under a monitor.
    draw.rectangle((2, 8, 10, 20), outline=_BLACK)  # system unit
    draw.rectangle((12, 3, 22, 15), outline=_BLACK)  # monitor
    draw.rectangle((14, 5, 20, 11), outline=_BLACK)  # screen
    return image


def draw_diag_cpu() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A chip: a square body with small pin ticks on each side.
    draw.rectangle((6, 6, 17, 17), outline=_BLACK)
    for x in (8, 11, 14, 17):
        draw.line((x, 3, x, 6), fill=_BLACK)
        draw.line((x, 17, x, 20), fill=_BLACK)
    return image


def draw_diag_mem() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A simple memory-module outline: a rectangle with notch marks.
    draw.rectangle((3, 8, 20, 15), outline=_BLACK)
    for x in range(5, 20, 3):
        draw.line((x, 8, x, 10), fill=_BLACK)
    return image


def draw_diag_io() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A small waveform/squiggle suggesting serial I/O activity.
    points = [(3, 12), (7, 6), (11, 18), (15, 6), (19, 18), (21, 12)]
    draw.line(points, fill=_BLACK)
    return image


def draw_diag_disk() -> Image.Image:
    image = _blank_canvas()
    draw = ImageDraw.Draw(image)
    # A simple square floppy-disk outline with a shutter notch.
    draw.rectangle((3, 3, 20, 20), outline=_BLACK)
    draw.rectangle((8, 3, 15, 9), outline=_BLACK)
    return image


_ICONS = {
    "macintosh.png": draw_macintosh,
    "lisa.png": draw_lisa,
    "next.png": draw_next,
    "apple2.png": draw_apple2,
    "ibmpc.png": draw_ibmpc,
    "diag_cpu.png": draw_diag_cpu,
    "diag_mem.png": draw_diag_mem,
    "diag_io.png": draw_diag_io,
    "diag_disk.png": draw_diag_disk,
}


def main() -> None:
    os.makedirs("icons", exist_ok=True)
    for filename, drawer in _ICONS.items():
        image = drawer()
        image.save(os.path.join("icons", filename))
        print(f"wrote icons/{filename}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_gen_icons.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Generate the real icon files the app will use**

Run: `python3 gen_icons.py`
Expected output: nine `wrote icons/....png` lines, and an `icons/`
directory now populated.

- [ ] **Step 6: Commit**

```bash
git add gen_icons.py tests/test_gen_icons.py icons/
git commit -m "Add procedural 1-bit icon generator and generated icons"
```

---

## Task 6: Rendering (dither background, panel, items)

**Files:**
- Create: `rendering.py`
- Test: `tests/test_rendering.py`

**Interfaces:**
- Consumes: `theme.*` (Task 1), `bitmap_font.render_text`/`text_size`
  (Task 2)
- Produces: `rendering.ItemVisual` (dataclass: `icon: pygame.Surface`,
  `label: str`, `status: str`, `selected: bool`),
  `rendering.draw_dither_background(surface: pygame.Surface) -> None`,
  `rendering.draw_panel(surface: pygame.Surface) -> pygame.Rect` (returns
  the panel's interior content rect, shadow already drawn),
  `rendering.draw_item(surface: pygame.Surface, center_x: int, top_y: int,
  item: ItemVisual) -> None`, `rendering.render_frame(surface:
  pygame.Surface, line1: str, line2: str, items: list[ItemVisual]) -> None`
  (composes background + panel + all items + text - the one function
  `launcher.py` calls every frame)

- [ ] **Step 1: Write the failing rendering tests**

`tests/test_rendering.py`:
```python
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
import theme
from rendering import ItemVisual, draw_dither_background, draw_panel, draw_item, render_frame


def _make_icon(color=(0, 0, 0)) -> pygame.Surface:
    icon = pygame.Surface((theme.ICON_SIZE, theme.ICON_SIZE))
    icon.fill((255, 255, 255))
    icon.fill(color, pygame.Rect(2, 2, theme.ICON_SIZE - 4, theme.ICON_SIZE - 4))
    return icon


def test_dither_background_is_not_solid_color():
    surface = pygame.Surface((theme.LOGICAL_WIDTH, theme.LOGICAL_HEIGHT))

    draw_dither_background(surface)

    colors = {surface.get_at((x, theme.LOGICAL_HEIGHT - 1))[:3] for x in range(0, 40)}
    assert len(colors) > 1, "dither background should mix black and white pixels"


def test_draw_panel_returns_interior_rect_within_panel_bounds():
    surface = pygame.Surface((theme.LOGICAL_WIDTH, theme.LOGICAL_HEIGHT))
    surface.fill((0, 0, 0))

    interior = draw_panel(surface)

    assert interior.left >= theme.PANEL_X
    assert interior.top >= theme.PANEL_Y
    assert interior.right <= theme.PANEL_X + theme.PANEL_WIDTH
    assert interior.bottom <= theme.PANEL_Y + theme.PANEL_HEIGHT
    # interior of the panel must be white
    assert surface.get_at((interior.left + 1, interior.top + 1))[:3] == (255, 255, 255)


def test_draw_item_selected_fills_area_black():
    surface = pygame.Surface((theme.LOGICAL_WIDTH, theme.LOGICAL_HEIGHT))
    surface.fill((255, 255, 255))
    item = ItemVisual(icon=_make_icon(), label="MEM", status="", selected=True)

    draw_item(surface, center_x=100, top_y=40, item=item)

    # somewhere in the item's footprint there should be a black background
    # pixel from the reverse-video fill (not just the icon's own black
    # pixels, which a non-selected icon would also have).
    footprint = pygame.Rect(100 - 40, 40, 80, 40)
    black_background_found = any(
        surface.get_at((x, y))[:3] == (0, 0, 0)
        for x in range(footprint.left, footprint.left + 5)
        for y in range(footprint.top, footprint.top + 5)
    )
    assert black_background_found


def test_render_frame_runs_without_error_with_multiple_items():
    surface = pygame.Surface((theme.LOGICAL_WIDTH, theme.LOGICAL_HEIGHT))
    items = [
        ItemVisual(icon=_make_icon(), label="LISA", status="", selected=True),
        ItemVisual(icon=_make_icon(), label="MACINTOSH", status="", selected=False),
    ]

    render_frame(surface, "SELECT SYSTEM...", "LISA / OFFICE SYSTEM 3.1", items)
    # no exception is the primary assertion; also sanity-check something
    # was actually drawn (not a blank surface).
    colors = {surface.get_at((x, y))[:3] for x in range(0, theme.LOGICAL_WIDTH, 10) for y in range(0, theme.LOGICAL_HEIGHT, 10)}
    assert len(colors) > 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_rendering.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'rendering'`

- [ ] **Step 3: Implement rendering**

`rendering.py`:
```python
"""Composes the dither background, the diagnostic/selection panel (with
its drop shadow), and the row of icon+label+status items onto the logical
512x384 surface. launcher.py scales the result up to the real screen."""

from dataclasses import dataclass

import pygame

import theme
from bitmap_font import render_text, text_size

_BLACK = (0, 0, 0)
_WHITE = (255, 255, 255)


@dataclass
class ItemVisual:
    icon: pygame.Surface
    label: str
    status: str
    selected: bool


def draw_dither_background(surface: pygame.Surface) -> None:
    surface.fill(_WHITE)
    tile_size = 4
    for y in range(0, surface.get_height(), tile_size):
        for x in range(0, surface.get_width(), tile_size):
            # A diagonal-hatch tile: pixels where (local_x + local_y) is
            # even are black, giving a 45-degree line pattern rather than
            # a checkerboard.
            for ty in range(tile_size):
                for tx in range(tile_size):
                    if (tx + ty) % 2 == 0:
                        surface.set_at((x + tx, y + ty), _BLACK)


def draw_panel(surface: pygame.Surface) -> pygame.Rect:
    shadow_rect = pygame.Rect(
        theme.PANEL_X + theme.SHADOW_OFFSET,
        theme.PANEL_Y + theme.SHADOW_OFFSET,
        theme.PANEL_WIDTH,
        theme.PANEL_HEIGHT,
    )
    surface.fill(_BLACK, shadow_rect)

    panel_rect = pygame.Rect(theme.PANEL_X, theme.PANEL_Y, theme.PANEL_WIDTH, theme.PANEL_HEIGHT)
    surface.fill(_WHITE, panel_rect)
    pygame.draw.rect(surface, _BLACK, panel_rect, width=1)

    interior = panel_rect.inflate(-4, -4)
    return interior


def draw_item(surface: pygame.Surface, center_x: int, top_y: int, item: ItemVisual) -> None:
    label_size = text_size(item.label)
    status_size = text_size(item.status) if item.status else (0, 0)

    content_width = max(theme.ICON_SIZE, label_size[0], status_size[0]) + 8
    content_height = label_size[1] + 4 + theme.ICON_SIZE + 4 + (status_size[1] if item.status else 0) + 8
    footprint = pygame.Rect(0, 0, content_width, content_height)
    footprint.centerx = center_x
    footprint.top = top_y

    fg_color = _WHITE if item.selected else _BLACK
    bg_color = _BLACK if item.selected else None

    if bg_color is not None:
        surface.fill(bg_color, footprint)

    label_rect = pygame.Rect(0, 0, *label_size)
    label_rect.centerx = center_x
    label_rect.top = footprint.top + 4
    render_text(surface, item.label, label_rect.left, label_rect.top, color=fg_color)

    icon_rect = pygame.Rect(0, 0, theme.ICON_SIZE, theme.ICON_SIZE)
    icon_rect.centerx = center_x
    icon_rect.top = label_rect.bottom + 4
    icon_to_draw = item.icon
    if item.selected:
        icon_to_draw = _invert_icon(item.icon)
    surface.blit(icon_to_draw, icon_rect)

    if item.status:
        status_rect = pygame.Rect(0, 0, *status_size)
        status_rect.centerx = center_x
        status_rect.top = icon_rect.bottom + 4
        render_text(surface, item.status, status_rect.left, status_rect.top, color=fg_color)


def _invert_icon(icon: pygame.Surface) -> pygame.Surface:
    inverted = icon.copy()
    width, height = inverted.get_size()
    for y in range(height):
        for x in range(width):
            r, g, b, *_ = inverted.get_at((x, y))
            inverted.set_at((x, y), (255 - r, 255 - g, 255 - b))
    return inverted


def render_frame(surface: pygame.Surface, line1: str, line2: str, items: list[ItemVisual]) -> None:
    draw_dither_background(surface)
    interior = draw_panel(surface)

    render_text(surface, line1, interior.left, interior.top, color=_BLACK)
    if line2:
        render_text(surface, line2, interior.left, interior.top + text_size(line1)[1] + 2, color=_BLACK)

    if items:
        spacing = theme.ICON_SPACING
        total_width = spacing * (len(items) - 1)
        start_x = interior.centerx - total_width // 2
        items_top = interior.top + theme.ITEMS_TOP_MARGIN
        for index, item in enumerate(items):
            draw_item(surface, start_x + index * spacing, items_top, item)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_rendering.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add rendering.py tests/test_rendering.py
git commit -m "Add dither background, panel, and item rendering"
```

---

## Task 7: Main application loop

**Files:**
- Create: `launcher.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `theme.*` (Task 1), `config.load_config` (Task 1),
  `bitmap_font` (Task 2, indirectly via `rendering`), `boot_diag.
  BootDiagnostic` (Task 3), `state.LauncherState`, `state.Phase` (Task 4),
  `rendering.ItemVisual`, `rendering.render_frame` (Task 6)
- Produces: `launcher.main() -> None` (the entry point; no other module
  depends on this one, so nothing downstream consumes its interface)

This task has no automated test — it's the real-time event loop and
subprocess/window integration, which needs actual hardware (a display, a
keyboard, a real emulator to launch) to verify meaningfully. Verification
is the manual checklist in Step 3.

- [ ] **Step 1: Implement the main loop**

`launcher.py`:
```python
"""Entry point: fullscreen pygame kiosk that shows the Lisa-style boot
diagnostic, then a keyboard-driven system picker, launching the selected
emulator as a subprocess and returning to the picker when it exits."""

import subprocess
import sys

import pygame

import theme
from bitmap_font import CHAR_WIDTH  # noqa: F401 (documents the font dependency)
from boot_diag import BootDiagnostic
from config import load_config
from rendering import ItemVisual, render_frame
from state import LauncherState, Phase

DIAG_ITEMS = ["CPU", "MEM", "I/O", "DISK"]


def _load_icon(path: str) -> pygame.Surface:
    return pygame.image.load(path).convert()


def _diag_items_visual(diag: BootDiagnostic, icons: dict[str, pygame.Surface]) -> list[ItemVisual]:
    items = []
    for index, name in enumerate(diag.items):
        icon_key = f"diag_{name.lower().replace('/', '')}"
        status = "OK" if index in diag.completed else ""
        items.append(ItemVisual(
            icon=icons[icon_key],
            label=name,
            status=status,
            selected=(index == diag.current_index),
        ))
    return items


def _system_items_visual(state: LauncherState, icons: dict[str, pygame.Surface]) -> list[ItemVisual]:
    items = []
    for index, system in enumerate(state.systems):
        items.append(ItemVisual(
            icon=icons[system.id],
            label=system.name,
            status="",
            selected=(index == state.selected_index),
        ))
    return items


def main() -> None:
    pygame.init()
    pygame.mouse.set_visible(False)

    real_screen = pygame.display.set_mode((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.FULLSCREEN)
    logical_surface = pygame.Surface((theme.LOGICAL_WIDTH, theme.LOGICAL_HEIGHT))
    clock = pygame.time.Clock()

    systems = load_config("config.json")

    icons: dict[str, pygame.Surface] = {}
    for system in systems:
        icons[system.id] = _load_icon(system.icon)
    for diag_name in DIAG_ITEMS:
        key = f"diag_{diag_name.lower().replace('/', '')}"
        icons[key] = _load_icon(f"icons/{key}.png")

    diag = BootDiagnostic(items=DIAG_ITEMS, step_seconds=theme.BOOT_DIAG_STEP_SECONDS)
    state = LauncherState(systems)

    running = True
    while running:
        dt = clock.tick(30) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and diag.done:
                if event.key == pygame.K_LEFT:
                    state.move_selection(-1)
                elif event.key == pygame.K_RIGHT:
                    state.move_selection(1)
                elif event.key == pygame.K_RETURN:
                    _launch_selected(state, real_screen)
                elif event.key == pygame.K_s:
                    subprocess.run(["systemctl", "poweroff"])
                elif event.key == pygame.K_r:
                    subprocess.run(["systemctl", "reboot"])

        if not diag.done:
            diag.update(dt)
            items = _diag_items_visual(diag, icons)
            line1, line2 = ("TESTING...", "")
        else:
            items = _system_items_visual(state, icons)
            line1, line2 = state.panel_lines()

        render_frame(logical_surface, line1, line2, items)
        scaled = pygame.transform.scale(logical_surface, (theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT))
        real_screen.blit(scaled, (0, 0))
        pygame.display.flip()

    pygame.quit()


def _launch_selected(state: LauncherState, real_screen: pygame.Surface) -> None:
    state.start_selected()
    pygame.display.iconify()
    try:
        subprocess.run(state.selected.command)
    finally:
        state.finish_starting()
        pygame.display.set_mode((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT), pygame.FULLSCREEN)


if __name__ == "__main__":
    sys.exit(main() or 0)
```

- [ ] **Step 2: Write the README**

`README.md`:
```markdown
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
or `S`/`R` to shut down/reboot on real hardware.

## Configuration

Edit `config.json` to add/remove systems. Each entry needs `id`, `name`,
`subtitle`, `icon` (path to a PNG), and `command` (an argv list, not a
shell string) that blocks until the emulator exits.

## Controls

- Left/Right arrow: change selection
- Enter: launch the selected system
- S: shut down the Pi
- R: reboot the Pi

## Running the tests

```
python3 -m pytest
```

## Installing as the boot-time kiosk

See `system/launcher.service` and the "Display/session integration"
section of the design spec for the minimal-X11-session autostart setup.
```

- [ ] **Step 3: Manual verification checklist**

On a development machine with a display (or the Pi itself once dependencies
are installed):
```
python3 gen_icons.py
python3 launcher.py
```
Confirm:
- The boot diagnostic shows `TESTING...`, sweeps reverse-video across
  CPU/MEM/I-O/DISK over roughly 1.5 seconds, each gaining an `OK` status
  as it completes.
- It then shows `SELECT SYSTEM...` with LISA selected (reverse video).
- Left/Right arrow keys move the selection and it clamps correctly at the
  single configured system (only one system exists yet, so this mostly
  confirms it doesn't crash - full multi-system movement gets a real test
  once Basilisk II is added to `config.json`).
- Pressing Enter shows `STARTING...` then `STARTING LISA...`, the window
  disappears, and the command in `config.json` actually runs.
- Quitting that command returns to `SELECT SYSTEM...` with no leftover
  visual state from the previous run.
- `S` and `R` correctly call `systemctl poweroff`/`reboot` (verify via
  `echo` substitution or reading the code, rather than actually powering
  off mid-test, unless you're ready for that).

- [ ] **Step 4: Commit**

```bash
git add launcher.py README.md
git commit -m "Add main application loop and README"
```

---

## Task 8: Pi boot integration (systemd, minimal X11 session, shutdown/reboot permissions)

**Files:**
- Create: `system/launcher.service`
- Create: `system/xsession-launcher.sh`
- Create: `system/10-lisa-launcher-power.rules` (a polkit JavaScript rules
  file; superseded the originally-planned `.pkla` format - see Step 3)

**Interfaces:**
- Consumes: nothing programmatic — these are OS integration files, not
  Python modules other tasks import.

This task is Pi-specific OS configuration with no automated test; it's
verified manually on the actual Pi (Step 4).

- [ ] **Step 1: Create the X session launcher script**

`system/xsession-launcher.sh`:
```bash
#!/bin/sh
# Started by launcher.service inside a minimal X session (no window
# manager, no desktop, no panel). Just runs the kiosk app.
cd /home/wottle/lisa-pi-launcher || exit 1
export SDL_VIDEODRIVER=x11
exec python3 launcher.py
```

- [ ] **Step 2: Create the systemd service**

`system/launcher.service`:
```ini
[Unit]
Description=Lisa-style boot launcher (kiosk)
After=graphical.target

[Service]
Type=simple
User=wottle
Environment=DISPLAY=:0
ExecStart=/usr/bin/xinit /home/wottle/lisa-pi-launcher/system/xsession-launcher.sh -- :0 vt1
Restart=always
RestartSec=2

[Install]
WantedBy=graphical.target
```

- [ ] **Step 3: Create the passwordless shutdown/reboot polkit rule**

Post-review update: the originally-planned `.pkla` (pklocalauthority) format
is only honored on current polkit via a separate `polkitd-pkla`
compatibility package that isn't guaranteed to be installed (e.g. stock
Raspberry Pi OS Trixie). Even where it is, `ResultActive=yes` only matches
an *active local session*, but `launcher.service` (Step 2) has no
`PAMName=`, so it gets no logind session at all - the rule wouldn't match.
It was also missing the `*-multiple-sessions` action ids, which logind
checks instead whenever another session exists (e.g. an SSH session used to
administer the Pi) - so `S`/`R` would fail whenever someone's also SSH'd
in. Using a polkit **rules file** instead avoids all three problems.

`system/10-lisa-launcher-power.rules`:
```js
polkit.addRule(function(action, subject) {
    var actions = [
        "org.freedesktop.login1.power-off",
        "org.freedesktop.login1.power-off-multiple-sessions",
        "org.freedesktop.login1.reboot",
        "org.freedesktop.login1.reboot-multiple-sessions",
    ];
    if (actions.indexOf(action.id) !== -1 && subject.user === "wottle") {
        return polkit.Result.YES;
    }
});
```

- [ ] **Step 4: Manual installation and verification on the Pi**

Ask the user to run these (interactive `sudo` required, matches project
convention of never running `sudo` on their behalf):
```
sudo cp system/launcher.service /etc/systemd/system/launcher.service
sudo cp system/10-lisa-launcher-power.rules /etc/polkit-1/rules.d/
chmod +x system/xsession-launcher.sh
sudo systemctl disable lightdm   # or whatever display manager currently autostarts the desktop
sudo systemctl enable launcher.service
sudo reboot
```
Confirm after reboot:
- The Linux desktop is never visible at any point.
- The launcher appears fullscreen automatically, boot diagnostic plays,
  picker appears.
- Enter launches LisaEm; quitting it returns to the picker.
- `S`/`R` shut down/reboot without any password prompt hanging the kiosk.
- `sudo systemctl kill launcher.service` (or killing the python process)
  confirms `Restart=always` respawns it within a couple seconds.

- [ ] **Step 5: Commit**

```bash
git add system/
git commit -m "Add systemd service, X session script, and power-control polkit rule"
```

---

## Self-Review Notes

- **Spec coverage:** boot diagnostic timing/sequence -> Task 3 +
  `_diag_items_visual` in Task 7; selection state + panel text per phase
  -> Task 4; reverse-video selection treatment (no borders/checkmarks) ->
  Task 6's `draw_item`; dither background -> Task 6; panel + drop shadow ->
  Task 6; hand-rolled bitmap font -> Task 2; procedural icons -> Task 5;
  config-driven systems -> Task 1; launch/wait/return subprocess behavior
  -> Task 7; systemd `Restart=always` + minimal X11 session + passwordless
  shutdown/reboot -> Task 8. All spec sections have a task.
- **Placeholder scan:** no TBD/TODO markers; every step has real, complete
  code. The two "Open items to resolve during implementation" from the
  spec (wrap-vs-clamp at list ends, polkit vs sudoers mechanism) were
  resolved concretely in Task 4 (clamp) and Task 8 (polkit).
- **Type consistency:** `SystemEntry` (Task 1) fields match usage in
  `state.py` (Task 4, `.name`/`.subtitle`/`.icon`/`.command`) and
  `launcher.py` (Task 7, same fields plus `.id` for icon lookup).
  `ItemVisual` (Task 6) fields (`icon`/`label`/`status`/`selected`) match
  construction call sites in `launcher.py`'s `_diag_items_visual`/
  `_system_items_visual`. `BootDiagnostic`'s `current_index`/`completed`/
  `done`/`items` (Task 3) match their usage in `launcher.py`. `LauncherState`'s
  `phase`/`selected_index`/`selected`/`systems`/`panel_lines()` (Task 4)
  match their usage in `launcher.py`.
