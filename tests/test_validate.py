#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import sys

import pytest

from myna.core import components
from myna.core.app.base import MynaApp
from myna.core.workflow.config import _strict_executable_validation


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


def test_validate_all_executable_false_disables_strict_default(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()
    app.settings = {"myna": {"validate_all_executable": False}}

    with pytest.warns(UserWarning, match="executable"):
        app.validate_executable(["definitely-not-installed-myna-executable"])


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
