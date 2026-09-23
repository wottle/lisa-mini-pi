import json
import os

import check_deps


def test_check_commands_reports_ok_for_a_command_on_path():
    results = check_deps._check_commands({"python3": "test"}, "fail")

    assert len(results) == 1
    assert results[0].startswith("[OK  ]")


def test_check_commands_reports_severity_for_a_missing_command():
    results = check_deps._check_commands({"not-a-real-command-xyz": "test"}, "fail")

    assert results[0].startswith("[FAIL]")
    assert "test" in results[0]


def test_check_commands_uses_given_severity_for_missing_optional_command():
    results = check_deps._check_commands({"not-a-real-command-xyz": "test"}, "warn")

    assert results[0].startswith("[WARN]")


def test_check_config_json_paths_flags_missing_file(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "systems": [
            {
                "id": "missing",
                "name": "MISSING",
                "subtitle": "TEST",
                "icon": "icons/does_not_exist.png",
                "command": ["/no/such/binary", "-k"],
            },
        ],
    }))

    results = check_deps._check_config_json_paths(str(config_path))

    assert any("FAIL" in r and "/no/such/binary" in r for r in results)
    assert any("FAIL" in r and "does_not_exist.png" in r for r in results)


def test_check_config_json_paths_reports_ok_for_a_real_file(tmp_path):
    real_file = tmp_path / "real_binary"
    real_file.write_text("#!/bin/sh\n")
    os.chmod(real_file, 0o755)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({
        "systems": [
            {
                "id": "real",
                "name": "REAL",
                "subtitle": "TEST",
                "icon": str(real_file),
                "command": [str(real_file)],
            },
        ],
    }))

    results = check_deps._check_config_json_paths(str(config_path))

    assert all("FAIL" not in r for r in results)


def test_check_config_json_paths_reports_error_for_unparseable_config(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("not valid json")

    results = check_deps._check_config_json_paths(str(config_path))

    assert len(results) == 1
    assert "FAIL" in results[0]


def test_check_paths_reports_ok_and_fail(tmp_path):
    real_file = tmp_path / "exists"
    real_file.write_text("x")
    missing_file = tmp_path / "does-not-exist"

    results = check_deps._check_paths([str(real_file), str(missing_file)], "thing")

    assert results[0].startswith("[OK  ]")
    assert results[1].startswith("[FAIL]")


def test_main_always_returns_zero_even_with_failures(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"systems": []}))
    monkeypatch.setattr(check_deps, "__file__", str(tmp_path / "check_deps.py"))
    monkeypatch.setattr(check_deps, "LOG_PATH", str(tmp_path / "log.txt"))

    exit_code = check_deps.main()

    assert exit_code == 0
    assert os.path.exists(tmp_path / "log.txt")
