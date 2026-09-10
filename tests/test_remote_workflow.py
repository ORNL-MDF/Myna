#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for detached interactive SSH workflow launchers."""

import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
import yaml

from myna.core.workflow import all as workflow_all
from myna.core.workflow import remote as remote_module


def _write_input(tmp_path, data_location="local", download="all"):
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        yaml.safe_dump(
            {
                "steps": [],
                "data": {"output_paths": {"demo": [str(tmp_path / "output.txt")]}},
                "myna": {
                    "compute": {
                        "host": "cloud",
                        "workdir": "/remote/myna-workspace",
                        "command": "/remote/venv/bin/myna",
                        "workspace": "/remote/workspaces/apps.yaml",
                        "data_location": data_location,
                        "download": download,
                    }
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return input_file


def _ssh_recorder(calls):
    def fake_ssh(host, command, input_text=None, capture_output=False):
        calls.append((host, command, input_text, capture_output))
        return SimpleNamespace(stdout="412\n")

    return fake_ssh


def test_compute_settings_accepts_remote_workspace_and_rejects_relative_path():
    settings = {
        "myna": {
            "compute": {
                "host": "cloud",
                "workdir": "/remote/work",
                "command": "/remote/venv/bin/myna",
                "workspace": "/remote/workspace.yaml",
                "data_location": "local",
            }
        }
    }
    assert (
        remote_module._get_compute_settings(settings)["workspace"]
        == "/remote/workspace.yaml"
    )
    settings["myna"]["compute"]["workspace"] = "workspace.yaml"
    with pytest.raises(ValueError, match="workspace"):
        remote_module._get_compute_settings(settings)


def test_launch_uses_immutable_snapshot_and_uuid_tracker(tmp_path, monkeypatch):
    input_file = _write_input(tmp_path)
    calls, configured = [], []
    monkeypatch.setattr(remote_module, "_ssh", _ssh_recorder(calls))
    monkeypatch.setattr(remote_module, "_scp_to", lambda *args: calls.append(args))
    monkeypatch.setattr(
        remote_module.config,
        "config",
        lambda filename: configured.append(Path(filename)),
    )

    tracker_path = remote_module.launch(input_file)
    tracker = remote_module._read_json(tracker_path)

    assert configured and configured[0] != input_file
    assert tracker["uuid"] in tracker["remote_dir"]
    assert tracker["uuid"] in tracker["result_dir"]
    assert tracker["input_file"] == str(input_file.resolve())
    assert Path(tracker["result_dir"]).parent.name == "myna_remote"
    ssh_calls = [call for call in calls if len(call) == 4]
    assert any("nohup" in command for _, command, _, _ in ssh_calls)
    assert "/remote/workspaces/apps.yaml" in ssh_calls[-1][1]


def test_launch_remote_data_serializes_input_before_detached_worker(
    tmp_path, monkeypatch
):
    input_file = _write_input(tmp_path, data_location="remote", download="outputs")
    calls = []
    monkeypatch.setattr(remote_module, "_ssh", _ssh_recorder(calls))

    tracker_path = remote_module.launch(input_file, step="demo")
    tracker = remote_module._read_json(tracker_path)

    serialized_calls = [call for call in calls if call[2] is not None]
    assert (
        json.loads(serialized_calls[0][2])["myna"]["compute"]["data_location"]
        == "remote"
    )
    assert tracker["step"] == "demo"
    assert calls[-1][3] is True and "nohup" in calls[-1][1]


def test_concurrent_launches_preserve_source_and_use_distinct_result_directories(
    tmp_path, monkeypatch
):
    input_file = _write_input(tmp_path)
    source_before = input_file.read_text(encoding="utf-8")
    calls = []
    monkeypatch.setattr(remote_module, "_ssh", _ssh_recorder(calls))
    monkeypatch.setattr(remote_module, "_scp_to", lambda *args: None)
    monkeypatch.setattr(remote_module.config, "config", lambda filename: None)

    first = remote_module._read_json(remote_module.launch(input_file))
    second = remote_module._read_json(remote_module.launch(input_file))

    assert first["uuid"] != second["uuid"]
    assert first["result_dir"] != second["result_dir"]
    assert input_file.read_text(encoding="utf-8") == source_before


def test_update_publishes_isolated_result_snapshot_and_cleans_remote(
    tmp_path, monkeypatch
):
    input_file = _write_input(tmp_path)
    tracker_path = tmp_path / ".myna" / "remote" / "abc.json"
    tracker = {
        "uuid": "abc",
        "input_file": str(input_file.resolve()),
        "host": "cloud",
        "remote_dir": "/remote/myna-abc",
        "remote_status": "/remote/myna-abc/myna_remote_status.json",
        "remote_results": "/remote/myna-abc/myna_remote_results.zip",
        "input_member": "input.yaml",
        "result_dir": str(tmp_path / "myna_remote" / "abc"),
        "download": "all",
        "retrieved": False,
    }
    remote_module._write_json(tracker_path, tracker)
    calls = []

    def fake_ssh(host, command, input_text=None, capture_output=False):
        calls.append(command)
        if capture_output:
            return SimpleNamespace(stdout=json.dumps({"state": "succeeded"}))
        return SimpleNamespace(stdout="")

    def fake_scp_from(host, source, destination):
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("input.yaml", input_file.read_text(encoding="utf-8"))
            archive.writestr("myna_output/result.txt", "result")

    monkeypatch.setattr(remote_module, "_ssh", fake_ssh)
    monkeypatch.setattr(remote_module, "_scp_from", fake_scp_from)
    updated = remote_module.update(input_file, tracker_path)

    result_dir = Path(updated["result_dir"])
    assert (result_dir / "input.yaml").exists()
    assert (result_dir / "myna_output" / "result.txt").read_text() == "result"
    assert not (tmp_path / "myna_output" / "result.txt").exists()
    assert updated["snapshot_input"] == str(result_dir / "input.yaml")
    assert any(command.startswith("rm -rf ") for command in calls)


def test_extract_bundle_rejects_path_traversal(tmp_path):
    bundle = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("../outside.txt", "unsafe")
    with pytest.raises(ValueError, match="unsafe path"):
        remote_module._extract_bundle(bundle, tmp_path / "target")


def test_main_dispatches_remote_command(monkeypatch):
    called = []
    monkeypatch.setattr(
        workflow_all.myna.core.workflow.remote,
        "parse",
        lambda parser: called.append(parser),
    )
    monkeypatch.setattr("sys.argv", ["myna", "remote"])
    workflow_all.main()
    assert len(called) == 1
