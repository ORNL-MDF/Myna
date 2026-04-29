#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import json
import sys

import pytest

from myna.application.cubit.cubit import CubitApp
from myna.application.deer.deer import DeerApp
from myna.application.exaca.exaca import ExaCA
from myna.application.openfoam.mesh_part_vtk.app import OpenFOAMMeshPartVTK
from myna.application.rve.rve import RVE
from myna.application.thesis.melt_pool_geometry_part import ThesisMeltPoolGeometryPart
from myna.application.thesis.solidification_part import ThesisSolidificationPart
from myna.application.thesis.thesis import Thesis
from myna.application.thesis.temperature_part import ThesisTemperaturePart
from myna.application.thesis.temperature_surface_part import (
    ThesisTemperatureSurfacePart,
)
from myna.core.app.base import MynaApp


def _count_option_actions(parser, option_string):
    return sum(option_string in action.option_strings for action in parser._actions)


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
    "app_cls",
    [
        ThesisTemperaturePart,
        ThesisSolidificationPart,
        ThesisMeltPoolGeometryPart,
    ],
)
@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_configure_arguments"),
    ],
)
def test_thesis_part_layer_configure_parsers_register_initial_temperature_arguments(
    monkeypatch, app_cls, stage_calls
):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = app_cls()
    app._validate_thesis_executable = False

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--initial-temperature-file") == 1
    assert _count_option_actions(app.parser, "--no-auto-initial-temperature") == 1
    assert app.args.initial_temperature_file is None
    assert app.args.auto_initial_temperature is True


@pytest.mark.parametrize(
    "stage_calls",
    [
        ("parse_execute_arguments", "parse_configure_arguments"),
        ("parse_configure_arguments", "parse_execute_arguments"),
        ("parse_execute_arguments", "parse_execute_arguments"),
    ],
)
def test_temperature_surface_part_stage_parsers_are_idempotent(
    monkeypatch, stage_calls
):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = ThesisTemperatureSurfacePart()
    app._validate_thesis_executable = False

    for stage_call in stage_calls:
        getattr(app, stage_call)()

    assert _count_option_actions(app.parser, "--res") == 1
    assert _count_option_actions(app.parser, "--wait") == 1
    assert _count_option_actions(app.parser, "--use-prior-layer-average") == 1
    assert app.args.res == pytest.approx(100e-6)
    assert app.args.wait == pytest.approx(0.0)
    assert app.args.use_prior_layer_average is False


@pytest.mark.parametrize(
    "stage_call",
    [
        "parse_configure_arguments",
        "parse_execute_arguments",
    ],
)
def test_temperature_surface_part_stage_parsers_set_default_executable(
    monkeypatch, stage_call
):
    monkeypatch.setattr(sys, "argv", ["test"])
    app = ThesisTemperatureSurfacePart()
    app._validate_thesis_executable = False

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
