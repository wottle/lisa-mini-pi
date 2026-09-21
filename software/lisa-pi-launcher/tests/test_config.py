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
