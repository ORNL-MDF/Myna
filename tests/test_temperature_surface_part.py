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

import pandas as pd
import pytest

from myna.application.thesis import read_parameter
from myna.application.thesis.temperature_surface_part import (
    ThesisTemperatureSurfacePart,
)
from myna.core.components import (
    ComponentTemperatureSurfacePart,
    return_step_class,
)


def _write_part_layer_case_metadata(case_dir, *, part, layer, preheat=450.0):
    case_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "build": {
            "parts": {
                part: {
                    "layer_data": {
                        str(layer): {
                            "scanpath": {"file_local": "scanpath.txt"},
                        }
                    }
                }
            },
            "build_data": {
                "preheat": {"value": preheat},
            },
        }
    }
    (case_dir / "myna_data.yaml").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_temperature_surface_part_component_lookup():
    component = return_step_class("temperature_surface_part")
    assert isinstance(component, ComponentTemperatureSurfacePart)


def test_temperature_surface_part_average_temperature(tmp_path):
    output_file = tmp_path / "previous.csv"
    pd.DataFrame({"T (K)": [300.0, 320.0, 340.0]}).to_csv(output_file, index=False)

    app = ThesisTemperatureSurfacePart()

    assert app._get_average_temperature(output_file) == pytest.approx(320.0)


def test_temperature_surface_part_resolves_direct_snapshot_file(tmp_path):
    snapshot_file = tmp_path / "snapshot.csv"
    snapshot_file.write_text("x,y,z,T\n0,0,0,300.0\n", encoding="utf-8")

    app = ThesisTemperatureSurfacePart()

    assert app._resolve_snapshot_file(snapshot_file) == snapshot_file


def test_temperature_surface_part_missing_previous_output_uses_preheat(tmp_path):
    material_file = tmp_path / "Material.txt"
    material_file.write_text("Constants\n{\n\tT_0\t298.15\n}\n", encoding="utf-8")

    app = ThesisTemperatureSurfacePart()
    app._set_initial_temperature(tmp_path, 410.0, tmp_path / "missing.csv")

    assert float(read_parameter(material_file, "T_0")[0]) == pytest.approx(410.0)


def test_temperature_surface_part_interface_dependencies_use_cross_part_predecessor(
    monkeypatch,
    tmp_path,
):
    first_case = tmp_path / "P1" / "99" / "surface"
    second_case = tmp_path / "P2" / "100" / "surface"
    third_case = tmp_path / "P2" / "101" / "surface"
    _write_part_layer_case_metadata(first_case, part="P1", layer=99)
    _write_part_layer_case_metadata(second_case, part="P2", layer=100)
    _write_part_layer_case_metadata(third_case, part="P2", layer=101)

    first_output = str(first_case / "temperature_surface.csv")
    second_output = str(second_case / "temperature_surface.csv")
    third_output = str(third_case / "temperature_surface.csv")
    myna_files = [first_output, second_output, third_output]

    app = ThesisTemperatureSurfacePart()
    app.args = SimpleNamespace(batch=False)
    app.settings = {
        "data": {
            "build": {
                "part_layer_interfaces": [
                    {
                        "part": "P2",
                        "layer": 100,
                        "previous_part": "P1",
                        "previous_layer": 99,
                    }
                ]
            }
        }
    }

    initial_temperature_calls = []

    def _record_initial_temperature(case_dir, _preheat, previous_output=None):
        settings = app._load_case_settings(case_dir)
        initial_temperature_calls.append(
            (app._get_case_part_and_layer_index(settings), previous_output)
        )

    monkeypatch.setattr(app, "_set_initial_temperature", _record_initial_temperature)
    monkeypatch.setattr(
        app,
        "run_case",
        lambda proc_list: ("snapshot.csv", proc_list),
    )
    monkeypatch.setattr(app, "_write_myna_output_from_pattern", lambda *_args: None)

    app._execute_part_interface_dependent_cases(myna_files)

    assert initial_temperature_calls == [
        (("P1", 99), None),
        (("P2", 100), first_output),
        (("P2", 101), second_output),
    ]


def test_temperature_surface_part_execute_uses_interface_path_when_configured(
    monkeypatch,
):
    app = ThesisTemperatureSurfacePart()
    app.args = SimpleNamespace(use_prior_layer_average=True)
    app.settings = {
        "data": {
            "build": {
                "part_layer_interfaces": [
                    {
                        "part": "P2",
                        "layer": 100,
                        "previous_part": "P1",
                        "previous_layer": 99,
                    }
                ]
            }
        }
    }

    called = {"interface": False}
    myna_files = ["file_0.csv", "file_1.csv"]

    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: myna_files)
    monkeypatch.setattr(
        app,
        "_execute_independent_cases",
        lambda _: pytest.fail("independent execution path should not be used"),
    )
    monkeypatch.setattr(
        app,
        "_execute_dependent_cases",
        lambda _: pytest.fail("default dependent execution path should not be used"),
    )
    monkeypatch.setattr(
        app,
        "_execute_part_interface_dependent_cases",
        lambda files, interface_index=None: called.__setitem__(
            "interface",
            files == myna_files and interface_index == {("P2", 100): ("P1", 99)},
        ),
    )

    app.execute()

    assert called["interface"] is True


def test_temperature_surface_part_execute_uses_independent_path_without_prior_average(
    monkeypatch,
):
    app = ThesisTemperatureSurfacePart()
    app.args = SimpleNamespace(use_prior_layer_average=False)

    called = {"independent": False}
    myna_files = ["file_0.csv", "file_1.csv"]

    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: myna_files)
    monkeypatch.setattr(
        app,
        "_execute_independent_cases",
        lambda files: called.__setitem__("independent", files == myna_files),
    )
    monkeypatch.setattr(
        app,
        "_execute_dependent_cases",
        lambda _: pytest.fail("dependent execution path should not be used"),
    )

    app.execute()

    assert called["independent"] is True
