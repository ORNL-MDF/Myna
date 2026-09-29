#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import argparse
import datetime
import importlib
import sys
from types import SimpleNamespace

import yaml

from .example_paths import REPO_ROOT


def test_peregrine_cli(monkeypatch, tmp_path):
    """Check launcher input generation and stage orchestration without an app."""
    launcher = importlib.import_module("myna.core.workflow.launch_from_peregrine")
    timestamp = datetime.datetime(2026, 9, 25, 12, 30)
    build_dir = tmp_path / "build with spaces"
    tmp_dir = tmp_path / "myna_tmp"
    workspace = (
        REPO_ROOT
        / "src"
        / "myna"
        / "cli"
        / "peregrine_launcher"
        / "peregrine_default_workspace.yaml"
    )
    stage_calls = []

    class FixedDateTime:
        @classmethod
        def now(cls):
            return timestamp

    def fake_run(command, **kwargs):
        stage_calls.append((command, kwargs))
        return SimpleNamespace(stdout=b"stage output")

    monkeypatch.setattr(launcher.datetime, "datetime", FixedDateTime)
    monkeypatch.setattr(launcher.subprocess, "run", fake_run)

    # Set up command line argument
    parser = argparse.ArgumentParser("test")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test",
            "--build",
            str(build_dir),
            "--parts",
            "[P5]",
            "--layers",
            "[50]",
            "--workspace",
            str(workspace),
            "--mode",
            "meltpool_geometry",
            "--tmp-dir",
            str(tmp_dir),
        ],
    )
    launcher.launch_from_peregrine(parser)

    working_dir = tmp_dir / "Myna_Temporary_Files" / "2026-09-25-12h-30m"
    configured_input = working_dir / "input_meltpool_geometry_2026-09-25-12h-30m.yaml"
    expected_commands = [
        f'myna {stage} --input "{configured_input}"'
        for stage in ("config", "run", "sync")
    ]
    assert [command for command, _ in stage_calls] == expected_commands
    for _, kwargs in stage_calls:
        assert kwargs == {
            "shell": True,
            "stdout": launcher.subprocess.PIPE,
            "stderr": launcher.subprocess.STDOUT,
        }

    output_dir = build_dir / "Myna"
    copied_input = output_dir / configured_input.name
    with open(copied_input, encoding="utf-8") as file:
        input_data = yaml.safe_load(file)
    assert input_data["data"]["build"] == {
        "datatype": "Peregrine",
        "name": "build_with_spaces_2026-09-25-12h-30m",
        "path": str(build_dir),
        "parts": {"P5": {"layers": [50]}},
    }
    assert input_data["myna"]["workspace"] == str(workspace)
    assert "steps" in input_data

    log_file = output_dir / "launch_from_peregrine_2026-09-25-12h-30m.log"
    assert log_file.exists()
    assert "stage output" in log_file.read_text(encoding="utf-8")
    assert not working_dir.exists()
