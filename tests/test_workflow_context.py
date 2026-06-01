#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import importlib
from importlib.machinery import ModuleSpec
import os
import sys
import types

import pytest

from myna.core.app.base import MynaApp
from myna.core.components.component import Component
import myna.core.components
from myna.core.context import current_workflow_context, workflow_context
from myna.core.files.file import File
from myna.core.workflow.run import run


WORKFLOW_ENV_KEYS = [
    "MYNA_INPUT",
    "MYNA_RUN_INPUT",
    "MYNA_SYNC_INPUT",
    "MYNA_STEP_NAME",
    "MYNA_STEP_CLASS",
    "MYNA_STEP_INDEX",
    "MYNA_LAST_STEP_NAME",
    "MYNA_LAST_STEP_CLASS",
]


def _clear_workflow_env(monkeypatch):
    for key in WORKFLOW_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_myna_app_reads_explicit_workflow_context(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setattr(sys, "argv", ["test"])
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        """
steps:
- demo:
    class: demo_class
    application: demo_app
data: {}
myna: {}
""",
        encoding="utf-8",
    )

    with workflow_context(
        input_file=os.fspath(input_file),
        step_name="demo",
        step_class="demo_class",
        step_index=0,
        last_step_name="previous",
    ):
        app = MynaApp()

    assert app.input_file == os.fspath(input_file)
    assert app.step_name == "demo"
    assert app.step_class == "demo_class"
    assert app.step_number == 0
    assert app.last_step_name == "previous"


def test_component_runs_stage_with_context_without_env(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        "steps: []\ndata:\n  build:\n    name: build\nmyna: {}\n",
        encoding="utf-8",
    )
    module_name = "myna.application.fakeapp.fakeclass.configure"
    captured = {}
    original_import_module = importlib.import_module

    def configure():
        context = current_workflow_context()
        captured["context"] = context
        captured["argv"] = list(sys.argv)
        captured["env_step"] = os.environ.get("MYNA_STEP_NAME")

    fake_module = types.SimpleNamespace(configure=configure)

    def fake_find_spec(name):
        if name == module_name:
            return ModuleSpec(name, loader=None, origin="/tmp/configure.py")
        return None

    def fake_import_module(name):
        if name == module_name:
            return fake_module
        return original_import_module(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    component = Component()
    component.name = "demo"
    component.component_application = "fakeapp"
    component.component_class = "fakeclass"
    component.input_file = os.fspath(input_file)
    component.step_index = 1
    component.last_step_name = "previous"
    component.configure_dict = {"example": "value"}
    component.data = {"build": {"name": "build"}}

    previous_argv = list(sys.argv)
    component.run_component()

    assert captured["context"].input_file == os.fspath(input_file)
    assert captured["context"].step_name == "demo"
    assert captured["context"].step_class == "fakeclass"
    assert captured["context"].step_index == 1
    assert captured["context"].last_step_name == "previous"
    assert captured["argv"] == ["/tmp/configure.py", "--example", "value"]
    assert captured["env_step"] is None
    assert sys.argv == previous_argv


def test_run_passes_workflow_context_without_setting_env(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        """
steps:
- first:
    class: first_class
    application: fake
- second:
    class: second_class
    application: fake
data:
  build:
    name: build
myna: {}
""",
        encoding="utf-8",
    )
    calls = []

    class DummyComponent(Component):
        def run_component(self):
            calls.append(
                {
                    "name": self.name,
                    "class": self.component_class,
                    "input_file": self.input_file,
                    "step_index": self.step_index,
                    "last_step_name": self.last_step_name,
                    "env_step": os.environ.get("MYNA_STEP_NAME"),
                }
            )

    monkeypatch.setattr(
        myna.core.components,
        "return_step_class",
        lambda component_class_name: DummyComponent(),
    )

    run(os.fspath(input_file))

    assert calls == [
        {
            "name": "first",
            "class": "first_class",
            "input_file": os.path.abspath(input_file),
            "step_index": 0,
            "last_step_name": "",
            "env_step": None,
        },
        {
            "name": "second",
            "class": "second_class",
            "input_file": os.path.abspath(input_file),
            "step_index": 1,
            "last_step_name": "first",
            "env_step": None,
        },
    ]
    for key in WORKFLOW_ENV_KEYS:
        assert key not in os.environ


class MissingOutputFile(File):
    """Output file type used to exercise run-time validation."""

    def __init__(self, file):
        super().__init__(file)
        self.filetype = ".csv"

    def file_is_valid(self):
        return True


def test_component_run_raises_when_execute_does_not_produce_output(
    monkeypatch, tmp_path
):
    _clear_workflow_env(monkeypatch)
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        "steps: []\ndata:\n  build:\n    name: build\nmyna: {}\n",
        encoding="utf-8",
    )
    module_name = "myna.application.fakeapp.fakeclass.execute"
    original_import_module = importlib.import_module

    def execute():
        return None

    fake_module = types.SimpleNamespace(execute=execute)

    def fake_find_spec(name):
        if name == module_name:
            return ModuleSpec(name, loader=None, origin="/tmp/execute.py")
        return None

    def fake_import_module(name):
        if name == module_name:
            return fake_module
        return original_import_module(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    component = Component()
    component.name = "demo"
    component.component_application = "fakeapp"
    component.component_class = "fakeclass"
    component.input_file = os.fspath(input_file)
    component.data = {"build": {"name": "build"}}
    component.output_requirement = MissingOutputFile
    component.output_template = "result.csv"

    with pytest.raises(
        RuntimeError,
        match="Only found 0 valid output files out of 1 output files for step demo",
    ):
        component.run_component()
