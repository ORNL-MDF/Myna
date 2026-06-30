#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import importlib
import os
import sys
import types

import pytest
from myna.core.app.base import MynaApp
from myna.core.components.component import Component
import myna.core.components
from myna.core.context import (
    WorkflowContext,
    current_workflow_context,
    get_workflow_context,
    get_workflow_input_file,
    workflow_context,
)
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


def test_get_workflow_context_prefers_explicit_context_over_env(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    input_file = tmp_path / "input.yaml"
    input_file.write_text("steps: []\n", encoding="utf-8")
    monkeypatch.setenv("MYNA_INPUT", "wrong-input.yaml")
    monkeypatch.setenv("MYNA_STEP_NAME", "wrong-step")

    with workflow_context(
        input_file=os.fspath(input_file),
        step_name="demo",
        step_class="demo_class",
        step_index=7,
        last_step_name="previous",
        last_step_class="previous_class",
    ):
        context = get_workflow_context()

    assert context == WorkflowContext(
        input_file=os.fspath(input_file),
        step_name="demo",
        step_class="demo_class",
        step_index=7,
        last_step_name="previous",
        last_step_class="previous_class",
    )


def test_get_workflow_context_falls_back_to_legacy_env(monkeypatch):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setenv("MYNA_INPUT", "/tmp/input.yaml")
    monkeypatch.setenv("MYNA_STEP_NAME", "demo")
    monkeypatch.setenv("MYNA_STEP_CLASS", "demo_class")
    monkeypatch.setenv("MYNA_STEP_INDEX", "3")
    monkeypatch.setenv("MYNA_LAST_STEP_NAME", "previous")
    monkeypatch.setenv("MYNA_LAST_STEP_CLASS", "previous_class")

    assert get_workflow_context() == WorkflowContext(
        input_file="/tmp/input.yaml",
        step_name="demo",
        step_class="demo_class",
        step_index=3,
        last_step_name="previous",
        last_step_class="previous_class",
    )


def test_get_workflow_context_returns_none_without_state(monkeypatch):
    _clear_workflow_env(monkeypatch)

    assert get_workflow_context() is None


def test_get_workflow_input_file_uses_shared_context_resolution(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    input_file = tmp_path / "input.yaml"
    input_file.write_text("steps: []\n", encoding="utf-8")

    assert get_workflow_input_file(default="fallback.yaml") == "fallback.yaml"

    monkeypatch.setenv("MYNA_INPUT", os.fspath(input_file))
    assert get_workflow_input_file() == os.fspath(input_file)


def test_get_workflow_context_invalid_step_index_raises_value_error(monkeypatch):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setenv("MYNA_STEP_INDEX", "not-an-int")

    try:
        get_workflow_context()
    except ValueError:
        pass
    else:
        raise AssertionError("Expected invalid MYNA_STEP_INDEX to raise ValueError")


def test_myna_app_reads_legacy_workflow_env(monkeypatch, tmp_path):
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
    monkeypatch.setenv("MYNA_INPUT", os.fspath(input_file))
    monkeypatch.setenv("MYNA_STEP_NAME", "demo")
    monkeypatch.setenv("MYNA_STEP_CLASS", "demo_class")
    monkeypatch.setenv("MYNA_STEP_INDEX", "0")
    monkeypatch.setenv("MYNA_LAST_STEP_NAME", "previous")

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
    monkeypatch.setenv("MYNA_APP_PATH", "/tmp/myna-apps")

    def configure():
        context = current_workflow_context()
        captured["context"] = context
        captured["argv"] = list(sys.argv)
        captured["env"] = {
            "input": os.environ.get("MYNA_INPUT"),
            "run_input": os.environ.get("MYNA_RUN_INPUT"),
            "step": os.environ.get("MYNA_STEP_NAME"),
            "step_class": os.environ.get("MYNA_STEP_CLASS"),
            "step_index": os.environ.get("MYNA_STEP_INDEX"),
            "last_step": os.environ.get("MYNA_LAST_STEP_NAME"),
        }

    fake_module = types.SimpleNamespace(configure=configure)

    def fake_import_module(name):
        if name == module_name:
            return fake_module
        return original_import_module(name)

    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: path == "/tmp/myna-apps/fakeapp/fakeclass/configure.py",
    )
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
    assert captured["argv"] == [
        "/tmp/myna-apps/fakeapp/fakeclass/configure.py",
        "--example",
        "value",
    ]
    assert captured["env"] == {
        "input": os.fspath(input_file),
        "run_input": os.fspath(input_file),
        "step": "demo",
        "step_class": "fakeclass",
        "step_index": "1",
        "last_step": "previous",
    }
    assert sys.argv == previous_argv
    for key in WORKFLOW_ENV_KEYS:
        assert key not in os.environ


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


def test_component_restores_cwd_after_stage_failure(monkeypatch, tmp_path):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setenv("MYNA_APP_PATH", "/tmp/myna-apps")
    input_file = tmp_path / "input.yaml"
    input_file.write_text(
        "steps: []\ndata:\n  build:\n    name: build\n", encoding="utf-8"
    )
    stage_dir = tmp_path / "stage-dir"
    stage_dir.mkdir()
    module_name = "myna.application.fakeapp.fakeclass.execute"
    original_import_module = importlib.import_module
    captured = {}

    def execute():
        os.chdir(stage_dir)
        captured["cwd_during_stage"] = os.getcwd()
        captured["env_step"] = os.environ.get("MYNA_STEP_NAME")
        raise RuntimeError("boom")

    fake_module = types.SimpleNamespace(execute=execute)

    def fake_import_module(name):
        if name == module_name:
            return fake_module
        return original_import_module(name)

    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: path == "/tmp/myna-apps/fakeapp/fakeclass/execute.py",
    )
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    component = Component()
    component.name = "demo"
    component.component_application = "fakeapp"
    component.component_class = "fakeclass"
    component.input_file = os.fspath(input_file)
    component.step_index = 2
    component.last_step_name = "previous"
    component.execute_dict = {"overwrite": True}
    component.data = {"build": {"name": "build"}}

    previous_cwd = os.getcwd()
    previous_argv = list(sys.argv)
    with pytest.raises(RuntimeError, match="boom"):
        component._run_stage("execute")

    assert captured["cwd_during_stage"] == os.fspath(stage_dir)
    assert captured["env_step"] == "demo"
    assert os.getcwd() == previous_cwd
    assert sys.argv == previous_argv
    for key in WORKFLOW_ENV_KEYS:
        assert key not in os.environ


def test_component_stage_missing_skips_without_import(monkeypatch):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setenv("MYNA_APP_PATH", "/tmp/myna-apps")
    import_called = False

    def fake_import_module(name):
        nonlocal import_called
        import_called = True
        return importlib.import_module(name)

    monkeypatch.setattr(os.path, "exists", lambda path: False)
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    component = Component()
    component.component_application = "fakeapp"
    component.component_class = "fakeclass"

    assert component._run_stage("configure") is False
    assert import_called is False


def test_component_stage_import_error_is_not_treated_as_missing(monkeypatch):
    _clear_workflow_env(monkeypatch)
    monkeypatch.setenv("MYNA_APP_PATH", "/tmp/myna-apps")
    module_name = "myna.application.fakeapp.fakeclass.configure"

    def fake_import_module(name):
        if name == module_name:
            raise ModuleNotFoundError("No module named 'vtk'")
        return importlib.import_module(name)

    monkeypatch.setattr(
        os.path,
        "exists",
        lambda path: path == "/tmp/myna-apps/fakeapp/fakeclass/configure.py",
    )
    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    component = Component()
    component.component_application = "fakeapp"
    component.component_class = "fakeclass"

    with pytest.raises(ModuleNotFoundError, match="vtk"):
        component._run_stage("configure")
