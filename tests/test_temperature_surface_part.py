#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
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
