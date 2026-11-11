#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import sys
import os
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
import oslex

from myna.core import components
from myna.core.app.base import MynaApp
from myna.core.workflow import validate as validate_workflow
from myna.core.workflow.config import _strict_executable_validation
from myna.core.workflow import validate as validate_module


def test_config_executable_validation_is_strict_by_default():
    assert _strict_executable_validation({}) is True
    assert _strict_executable_validation({"myna": {}}) is True


def test_config_executable_validation_setting_can_opt_out():
    assert (
        _strict_executable_validation({"myna": {"validate_all_executable": False}})
        is False
    )


def test_validate_executable_can_be_strict(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    with pytest.raises(FileNotFoundError, match="executable"):
        app.validate_executable(
            ["definitely-not-installed-myna-executable"], strict=True
        )


@pytest.mark.skipif(os.name == "nt", reason="environment setup uses a POSIX shell")
def test_validate_executable_quotes_paths_with_environment(monkeypatch, tmp_path):
    executable = tmp_path / "tool $(touch injected)"
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    env_file = tmp_path / "setup environment.sh"
    env_file.write_text(":\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["test", "--env", str(env_file)])

    MynaApp().validate_executable([executable], strict=True)

    assert not (tmp_path / "injected").exists()


def test_validate_executable_quotes_docker_command(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test", "--docker-image", "example"])
    captured = {}

    class Process:
        name = "test-container"

        def communicate(self, timeout=None):
            return b"", b""

        def wait(self, timeout=None):
            return 0

    def run(image, command, **kwargs):
        captured["command"] = command
        return Process()

    monkeypatch.setattr(
        "myna.core.app.base.docker.from_env",
        lambda: SimpleNamespace(containers=SimpleNamespace(run=run)),
    )
    monkeypatch.setattr(oslex, "quote", lambda _: pytest.fail("used host quoting"))
    executable = "/opt/my tools/$(touch injected)"
    MynaApp().validate_executable([executable], strict=True)

    assert captured["command"][:2] == ["bash", "-lc"]
    assert oslex.split_sh(captured["command"][2]) == ["which", executable]


def test_validate_all_executable_false_disables_strict_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()
    app.settings = {"myna": {"validate_all_executable": False}}

    with pytest.warns(UserWarning, match="executable"):
        app.validate_executable(["definitely-not-installed-myna-executable"])


def test_workflow_validate_passes_optional_strict_value(monkeypatch, tmp_path):
    input_file = tmp_path / "input.yaml"
    input_file.write_text("steps: []\n", encoding="utf-8")
    settings = {
        "steps": [{"step": {"class": "fake", "application": "fake"}}],
        "data": {},
        "myna": {},
    }
    calls = []

    class Step:
        def apply_settings(self, *args):
            pass

        def validate_executables(self, strict=None):
            calls.append(strict)

    monkeypatch.setattr(validate_module, "load_input", lambda _: settings)
    monkeypatch.setattr(
        validate_module.components, "return_step_class", lambda _: Step()
    )
    monkeypatch.setattr(
        validate_module, "workflow_context", lambda **_: nullcontext(None)
    )
    monkeypatch.setattr(validate_module, "workflow_env", lambda *_, **__: nullcontext())

    validate_module.validate(input_file, strict=False)

    assert calls == [False]


def test_validate_rejects_unknown_step_names(monkeypatch):
    monkeypatch.setattr(
        validate_workflow,
        "load_input",
        lambda _: {"steps": [{"configured": {}}]},
    )

    with pytest.raises(ValueError, match="Unknown step name.*typo"):
        validate_workflow.validate("input.yaml", "typo")


def test_validate_rejects_selection_that_matches_no_steps(monkeypatch):
    monkeypatch.setattr(
        validate_workflow,
        "load_input",
        lambda _: {"steps": []},
    )

    with pytest.raises(ValueError, match="Unknown step name"):
        validate_workflow.validate("input.yaml", "configured")


def test_component_validates_each_stage_requirement_in_its_stage_environment(
    monkeypatch,
):
    component = components.return_step_class("temperature_part_pvd")
    component.component_application = "adamantine"
    component.component_class = "temperature_part_pvd"
    component.name = "adamantine"
    component.data = {"build": {"name": "build"}}
    component.configure_dict = {}
    component.execute_dict = {
        "adamantine-bin": "/container/bin/adamantine",
        "docker-image": "rombur/adamantine:1.0",
    }

    validated = []

    def record_validation(self, executables, strict=None):
        validated.append((executables, strict, self.args.docker_image))

    monkeypatch.setattr(MynaApp, "validate_executable", record_validation)
    component.validate_executables()

    assert validated == [(["/container/bin/adamantine"], None, "rombur/adamantine:1.0")]


def test_component_validation_continues_after_stage_parser_system_exit(monkeypatch):
    component = components.return_step_class("temperature_part_pvd")
    component.component_application = "adamantine"
    component.component_class = "temperature_part_pvd"
    component.name = "adamantine"
    component.data = {"build": {"name": "build"}}
    component.configure_dict = {}
    component.execute_dict = {"adamantine-bin": "adamantine"}

    validated = []

    def record_validation(self, executables, strict=None):
        validated.append(executables)

    monkeypatch.setattr(MynaApp, "validate_executable", record_validation)
    monkeypatch.setattr(sys, "argv", ["myna", "--skip"])

    component.validate_executables()

    assert validated == [["adamantine"]]
    assert sys.argv == ["myna", "--skip"]
