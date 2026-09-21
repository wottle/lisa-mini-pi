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
