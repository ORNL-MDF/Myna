#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for the interactive SSH workflow launcher."""

import json
import sys
import zipfile

import pytest
import yaml

from myna.core.workflow import remote as remote_module
from myna.core.workflow import all as workflow_all


def _write_input(tmp_path, data_location="local", download="all"):
    output = tmp_path / "myna_output" / "result.txt"
    output.parent.mkdir()
    output.write_text("result", encoding="utf-8")
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        yaml.safe_dump(
            {
                "steps": [],
                "data": {"output_paths": {"demo": [str(output)]}},
                "myna": {
                    "compute": {
                        "host": "cloud",
                        "workdir": "/remote/myna-workspace",
                        "command": "/remote/venv/bin/myna",
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


def test_get_compute_settings_validates_required_remote_contract():
    settings = {
        "myna": {
            "compute": {
                "host": "cloud",
                "workdir": "/remote/work",
                "command": "/remote/venv/bin/myna",
                "data_location": "local",
            }
        }
    }
    compute = remote_module._get_compute_settings(settings)
    assert compute["download"] == "all"
    assert compute["python"] == "/remote/venv/bin/python"

    settings["myna"]["compute"]["data_location"] = "somewhere"
    with pytest.raises(ValueError, match="data_location"):
        remote_module._get_compute_settings(settings)


def test_remote_local_data_configures_uploads_and_cleans(tmp_path, monkeypatch):
    input_file = _write_input(tmp_path)
    calls = []

    monkeypatch.setattr(
        remote_module.config,
        "config",
        lambda filename: calls.append(("config", filename)),
    )
    monkeypatch.setattr(
        remote_module,
        "_ssh",
        lambda host, command, input_text=None: calls.append(
            ("ssh", host, command, input_text)
        ),
    )
    monkeypatch.setattr(
        remote_module,
        "_scp_to",
        lambda host, source, destination: calls.append(
            ("to", host, source, destination)
        ),
    )

    def fake_scp_from(host, source, destination):
        calls.append(("from", host, source, destination))
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("input.yaml", input_file.read_text(encoding="utf-8"))

    monkeypatch.setattr(remote_module, "_scp_from", fake_scp_from)
    remote_module.remote(input_file)

    assert calls[0][0] == "config"
    assert calls[1][2].startswith("mkdir -p ")
    assert calls[2][0] == "to"
    assert "myna_remote_bundle.zip" in calls[2][3]
    assert calls[3][0] == "ssh"
    assert 'command_args = [command, "run"' in remote_module._REMOTE_BOOTSTRAP
    assert calls[4][0] == "from"
    assert calls[5][0] == "ssh" and calls[5][2].startswith("rm -rf ")


def test_remote_remote_data_sends_json_and_retains_outputs_mode(tmp_path, monkeypatch):
    input_file = _write_input(tmp_path, data_location="remote", download="outputs")
    calls = []

    monkeypatch.setattr(
        remote_module,
        "_ssh",
        lambda host, command, input_text=None: calls.append(
            (host, command, input_text)
        ),
    )

    def fake_scp_from(host, source, destination):
        with zipfile.ZipFile(destination, "w") as archive:
            archive.writestr("input.yaml", input_file.read_text(encoding="utf-8"))

    monkeypatch.setattr(remote_module, "_scp_from", fake_scp_from)
    remote_module.remote(input_file, step="demo")

    assert len(calls) == 1
    assert (
        '[command, "config", "--input", str(input_path)]'
        in remote_module._REMOTE_BOOTSTRAP
    )
    assert 'command_args = [command, "run"' in remote_module._REMOTE_BOOTSTRAP
    assert calls[0][1].endswith(" demo outputs")
    serialized = json.loads(calls[0][2])
    assert serialized["myna"]["compute"]["data_location"] == "remote"


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
    monkeypatch.setattr(sys, "argv", ["myna", "remote"])
    workflow_all.main()
    assert len(called) == 1
