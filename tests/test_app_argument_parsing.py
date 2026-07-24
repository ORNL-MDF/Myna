#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import json
from types import SimpleNamespace
import sys
import stat

import pytest
import yaml

from myna.application.cubit.cubit import CubitApp
from myna.application.deer.deer import DeerApp
from myna.application.exaca.exaca import ExaCA
from myna.application.openfoam.mesh_part_vtk.app import OpenFOAMMeshPartVTK
from myna.application.rve.rve import RVE
from myna.application.thesis.thesis import Thesis
from myna.core.app.base import MynaApp


def _count_option_actions(parser, option_string):
    return sum(option_string in action.option_strings for action in parser._actions)


def _write_shell_executable(path, body):
    path.write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_register_argument_skips_duplicate_option_registration(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    app.register_argument(
        "--demo",
        default="value",
        type=str,
        help="Demo parser option for regression coverage",
    )
    app.register_argument(
        "--demo",
        default="value",
        type=str,
        help="Demo parser option for regression coverage",
    )
    app.parse_known_args()

    assert _count_option_actions(app.parser, "--demo") == 1
    assert app.args.demo == "value"


def test_register_argument_rejects_conflicting_option_redefinitions(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    app.register_argument(
        "--demo",
        default="value",
        type=str,
        help="Demo parser option for regression coverage",
    )

    with pytest.raises(ValueError, match="option '--demo'"):
        app.register_argument(
            "--demo",
            default="different",
            type=str,
            help="Demo parser option for regression coverage",
        )


def test_register_argument_deduplicates_across_hooks(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    app.register_argument(
        "--demo",
        default="value",
        type=str,
        help="Demo parser option for regression coverage",
    )
    app.register_argument(
        "--demo",
        default="value",
        type=str,
        help="Demo parser option for regression coverage",
    )
    app.parse_known_args()

    assert _count_option_actions(app.parser, "--demo") == 1
    assert app.args.demo == "value"


def test_register_argument_rejects_shadowing_base_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    with pytest.raises(ValueError, match="option '--np'"):
        app.register_argument(
            "--np",
            default=2,
            type=int,
            help="Conflicting processor override",
        )


def test_register_argument_skips_duplicate_positional_registration(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    app.register_argument("demo_positional")
    app.register_argument("demo_positional")

    positional_actions = [
        action for action in app.parser._actions if action.dest == "demo_positional"
    ]
    assert len(positional_actions) == 1


def test_register_argument_rejects_conflicting_positional_dest_redefinitions(
    monkeypatch,
):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    app.register_argument("demo_positional")

    with pytest.raises(ValueError, match="dest 'demo_positional'"):
        app.register_argument("demo_positional", nargs="?")


def test_myna_app_init_tolerates_missing_step_name(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["test"])
    input_file = tmp_path / "input.json"
    input_file.write_text(
        json.dumps(
            {
                "steps": [
                    {
                        "3dthesis": {
                            "class": "temperature_surface_part",
                            "application": "thesis",
                        }
                    }
                ],
                "data": {"output_paths": {"3dthesis": []}},
                "myna": {},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MYNA_INPUT", str(input_file))
    monkeypatch.delenv("MYNA_STEP_NAME", raising=False)

    app = MynaApp()

    assert app.step_name is None
    assert app.step_number is None
    assert app.component is None


def test_myna_app_registers_docker_config_argument(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = MynaApp()

    assert _count_option_actions(app.parser, "--docker-config") == 1
    assert app.args.docker_config is None


def test_start_subprocess_loads_docker_run_kwargs_from_config(monkeypatch, tmp_path):
    docker_config_file = tmp_path / "docker-run.yaml"
    docker_config_file.write_text(
        yaml.safe_dump({"remove": True, "volumes": {"/host": {"bind": "/data"}}}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test",
            "--docker-image",
            "example:latest",
            "--docker-config",
            str(docker_config_file),
        ],
    )

    captured = {}

    class FakeContainers:
        def run(self, image, command, **kwargs):
            captured["image"] = image
            captured["command"] = command
            captured["kwargs"] = kwargs
            return SimpleNamespace(name="fake-container")

    monkeypatch.setattr(
        "myna.core.app.base.docker.from_env",
        lambda: SimpleNamespace(containers=FakeContainers()),
    )

    app = MynaApp()
    app.start_subprocess(["echo", "hello"], volumes={"/addition": {"bind": "/work"}})

    assert captured["image"] == "example:latest"
    assert captured["command"] == ["-lc", "echo hello"]
    assert captured["kwargs"]["entrypoint"] == "bash"
    assert captured["kwargs"]["detach"] is True
    assert captured["kwargs"]["remove"] is True
    assert captured["kwargs"]["volumes"] == {
        "/host": {"bind": "/data"},
        "/addition": {"bind": "/work"},
    }


def test_start_subprocess_rejects_non_mapping_docker_config(monkeypatch, tmp_path):
    docker_config_file = tmp_path / "docker-run.yaml"
    docker_config_file.write_text("- remove\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "test",
            "--docker-image",
            "example:latest",
            "--docker-config",
            str(docker_config_file),
        ],
    )

    app = MynaApp()

    with pytest.raises(TypeError, match="mapping of docker run kwargs"):
        app.start_subprocess(["echo", "hello"])


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_deer_stage_parsers_are_idempotent(monkeypatch, stage_calls):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = DeerApp()

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--moosepath") == 1
    assert app.args.moosepath is None


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_cubit_stage_parsers_are_idempotent(monkeypatch, stage_calls):
    monkeypatch.setattr(sys, "argv", ["test"])
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitApp()

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--cubitpath") == 1
    assert app.args.cubitpath is None


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_thesis_stage_parsers_are_idempotent(monkeypatch, stage_calls):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = Thesis(validate_executable=False)

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--res") == 1
    assert _count_option_actions(app.parser, "--nout") == 1
    assert app.args.res == pytest.approx(12.5e-6)
    assert app.args.nout == 1000


@pytest.mark.parametrize(
    "stage_call",
    [
        "parse_configure_arguments",
        "parse_execute_arguments",
    ],
)
def test_thesis_stage_parsers_set_default_executable(monkeypatch, stage_call):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = Thesis(validate_executable=False)

    getattr(app, stage_call)()

    assert app.args.exec == "3DThesis"


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_exaca_stage_parsers_are_idempotent(monkeypatch, stage_calls):
    monkeypatch.setattr(sys, "argv", ["test"])
    monkeypatch.setattr(ExaCA, "validate_executable", lambda self, default: None)
    app = ExaCA()

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--cell-size") == 1
    assert _count_option_actions(app.parser, "--nd") == 1
    assert _count_option_actions(app.parser, "--mu") == 1
    assert _count_option_actions(app.parser, "--std") == 1
    assert _count_option_actions(app.parser, "--sub-size") == 1


@pytest.mark.parametrize(
    "stage_call",
    [
        "parse_configure_arguments",
        "parse_execute_arguments",
    ],
)
def test_exaca_stage_parsers_set_default_executable(monkeypatch, stage_call):
    monkeypatch.setattr(sys, "argv", ["test"])
    monkeypatch.setattr(ExaCA, "validate_executable", lambda self, default: None)
    app = ExaCA()

    getattr(app, stage_call)()

    if "execute" in stage_call:
        assert app.args.exec == "ExaCA"


def test_exaca_get_executable_version_reads_banner_before_missing_input_error(
    monkeypatch, tmp_path
):
    executable = tmp_path / "ExaCA"
    _write_shell_executable(
        executable,
        'printf "%s\\n" "ExaCA version: 2.1.0-dev"\n'
        'printf "%s\\n" "Error: Must provide path to input file" >&2\n'
        "exit 1\n",
    )
    monkeypatch.setattr(sys, "argv", ["test", "--exec", str(executable)])

    assert ExaCA().get_executable_version() == "2.1.0-dev"


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_postprocess_arguments"),
        ("parse_postprocess_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_rve_stage_parsers_are_idempotent(monkeypatch, stage_calls):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = RVE()

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--num-region") == 1
    assert _count_option_actions(app.parser, "--max-layers") == 1


def test_rve_selection_execute_parser_is_idempotent(monkeypatch):
    pytest.importorskip("matplotlib")
    pytest.importorskip("scipy")
    pytest.importorskip("skimage")
    from myna.application.rve.rve_selection.app import RVESelection

    monkeypatch.setattr(sys, "argv", ["test"])
    app = RVESelection()

    app.parse_execute_arguments()
    app.parse_execute_arguments()

    assert _count_option_actions(app.parser, "--num-region") == 1
    assert _count_option_actions(app.parser, "--max-layers") == 1
    assert _count_option_actions(app.parser, "--bid") == 1
    assert _count_option_actions(app.parser, "--max-layers-per-region") == 1


def test_openfoam_mesh_part_vtk_execute_parser_is_idempotent(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = OpenFOAMMeshPartVTK()

    app.parse_execute_arguments()
    app.parse_execute_arguments()

    assert _count_option_actions(app.parser, "--scale") == 1
    assert _count_option_actions(app.parser, "--coarse") == 1
    assert _count_option_actions(app.parser, "--refine") == 1
