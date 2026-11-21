"""The per-machine "start this one automatically at power-on" setting.

One system can be marked. It lives in a small file under
~/.config/lisa-launcher/ on each machine (not in config.json, which is
shared and committed), so different Pis can choose differently.

Auto-start happens once per power-on. The launcher notes the boot's unique
id the first time it starts in each boot - before it launches anything - and
a later start in the same boot (a watchdog restart after a hang, coming back
from the desktop, a service restart) therefore never retries the emulator.
If something is wrong with the settings, the boot id, or the ability to write
the note, the answer is always "show the picker".
"""

import os
from pathlib import Path

BOOT_ID_PATH = "/proc/sys/kernel/random/boot_id"


class AutoStart:
    def __init__(self, config_dir, boot_id_path=BOOT_ID_PATH):
        self._dir = Path(config_dir)
        self._marker = self._dir / "autostart"
        self._last_boot = self._dir / "last-boot-id"
        self._boot_id_path = Path(boot_id_path)

    @classmethod
    def default(cls):
        return cls(Path.home() / ".config" / "lisa-launcher")

    # -- the mark --------------------------------------------------------------

    def get(self):
        """The marked system's id, or None if nothing usable is set."""
        return self._read(self._marker)

    def toggle(self, system_id):
        """Mark `system_id` (moving the mark off any other), or clear it if it
        is already the marked one. Returns the marked id afterwards. If the
        setting can't be saved, nothing changes."""
        wanted = None if self.get() == system_id else system_id
        try:
            if wanted is None:
                self._marker.unlink(missing_ok=True)
            else:
                self._write(self._marker, wanted)
        except OSError:
            pass
        return self.get()

    # -- starting up -----------------------------------------------------------

    def startup(self, known_ids):
        """Called once each time the launcher starts. Returns the id of the
        system to launch straight away, or None to show the picker."""
        boot = self._read(self._boot_id_path)
        if boot is None:
            return None
        previous = self._read(self._last_boot)
        try:
            self._write(self._last_boot, boot)  # note this boot BEFORE launching anything
        except OSError:
            return None
        if previous == boot:
            return None
        marked = self.get()
        return marked if marked in known_ids else None

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _read(path):
        try:
            return Path(path).read_text(encoding="utf-8").strip() or None
        except (OSError, UnicodeDecodeError):
            return None

    def _write(self, path, text):
        self._dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        try:
            tmp.write_text(text + "\n", encoding="utf-8")
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
