#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest

from myna.application.deer.creep_timeseries_region import CreepTimeseriesRegionDeerApp


def _build_app(step_output_paths):
    app = CreepTimeseriesRegionDeerApp()
    app.step_name = "creep"
    app.settings = {"data": {"output_paths": {"creep": step_output_paths}}}
    return app


def test_get_case_mesh_path_ignores_existing_output_mesh(tmp_path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    staged_mesh = case_dir / "input_mesh.e"
    staged_mesh.write_text("", encoding="utf-8")
    (case_dir / "wCreep_out.e").write_text("", encoding="utf-8")

    app = _build_app([str(case_dir / "result.csv")])

    assert app.get_case_mesh_path(str(case_dir)) == str(staged_mesh)


def test_get_case_mesh_path_still_rejects_multiple_non_output_meshes(tmp_path):
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    (case_dir / "input_mesh_a.e").write_text("", encoding="utf-8")
    (case_dir / "input_mesh_b.exo").write_text("", encoding="utf-8")
    (case_dir / "wCreep_out.e").write_text("", encoding="utf-8")

    app = _build_app([str(case_dir / "result.csv")])

    with pytest.raises(FileNotFoundError, match="found 2"):
        app.get_case_mesh_path(str(case_dir))
