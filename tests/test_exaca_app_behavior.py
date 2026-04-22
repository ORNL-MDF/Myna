#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import json
import os
from types import SimpleNamespace

import pandas as pd

from myna.application.exaca.microstructure_region import ExaCAMicrostructureRegion
from myna.application.exaca.microstructure_region_slice import (
    ExaCAMicrostructureRegionSlice,
)
import myna.application.exaca.microstructure_region_slice.app as slice_app_module


def _write_settings(tmp_path, step_output_paths, last_step_output_paths):
    settings = {
        "steps": [
            {
                "solidification": {
                    "class": "solidification_region_reduced",
                    "application": "additivefoam",
                }
            },
            {
                "microstructure": {
                    "class": "microstructure_region",
                    "application": "exaca",
                }
            },
        ],
        "data": {
            "build": {
                "name": "build-1",
                "build_data": {"layer_thickness": {"value": 40e-6}},
                "parts": {"part-a": {"regions": {"region-1": {}, "region-2": {}}}},
            },
            "output_paths": {
                "solidification": last_step_output_paths,
                "microstructure": step_output_paths,
            },
        },
        "myna": {},
    }
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(settings), encoding="utf-8")
    return input_file


def _configure_workflow_env(monkeypatch, tmp_path, step_output_paths, solid_outputs):
    input_file = _write_settings(tmp_path, step_output_paths, solid_outputs)
    monkeypatch.setenv("MYNA_INPUT", str(input_file))
    monkeypatch.setenv("MYNA_STEP_NAME", "microstructure")
    monkeypatch.setenv("MYNA_LAST_STEP_NAME", "solidification")


def _configure_minimal_app_env(monkeypatch, tmp_path):
    """Set the minimum workflow environment required for app construction."""
    _configure_workflow_env(monkeypatch, tmp_path, [], [])


def _create_exaca_install(tmp_path):
    install_dir = tmp_path / "install"
    exe_path = install_dir / "bin" / "ExaCA"
    exe_path.parent.mkdir(parents=True)
    exe_path.write_text("#!/bin/sh\n", encoding="utf-8")
    exe_path.chmod(0o755)

    orientation_file = install_dir / "share" / "ExaCA" / "GrainOrientationVectors.csv"
    orientation_file.parent.mkdir(parents=True)
    orientation_file.write_text("phi1,Phi,phi2\n", encoding="utf-8")
    return exe_path, orientation_file


def _create_material_root(monkeypatch, tmp_path):
    app_root = tmp_path / "apps"
    material_file = app_root / "exaca" / "materials" / "SS316.json"
    material_file.parent.mkdir(parents=True)
    material_file.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("MYNA_APP_PATH", str(app_root))
    return material_file


def _write_template(template_dir, include_analysis):
    template_dir.mkdir(parents=True)
    (template_dir / "inputs.json").write_text(
        json.dumps(
            {
                "MaterialFileName": "",
                "GrainOrientationFile": "",
                "Domain": {"CellSize": 1.0, "LayerOffset": 1.0, "NumberOfLayers": 0},
                "TemperatureData": {"TemperatureFiles": []},
                "Nucleation": {
                    "Density": 0.0,
                    "MeanUndercooling": 0.0,
                    "StDev": 0.0,
                },
                "Substrate": {"MeanSize": 0.0},
                "Printing": {"PathToOutput": "./output", "OutputFile": "exaca"},
            }
        ),
        encoding="utf-8",
    )
    (template_dir / "runCase.sh").write_text(
        "BIN={{EXACA_BIN_PATH}}\nEXEC={{EXACA_EXEC}}\nNP={{RANKS}}\n",
        encoding="utf-8",
    )
    if include_analysis:
        (template_dir / "analysis.json").write_text(
            json.dumps(
                {
                    "Regions": {
                        "XY": {"zBounds": [0, 0]},
                        "XZ": {"yBounds": [0, 0]},
                        "YZ": {"xBounds": [0, 0]},
                    }
                }
            ),
            encoding="utf-8",
        )


def _write_case_metadata(case_dir):
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "myna_data.yaml").write_text(
        json.dumps(
            {
                "build": {
                    "build_data": {
                        "material": {"value": "SS316"},
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _build_app_args(template_dir, exe_path):
    return SimpleNamespace(
        template=str(template_dir),
        exec=str(exe_path),
        cell_size=2.5,
        nd=250.0,
        mu=5.0,
        std=0.5,
        sub_size=12.3,
        np=4,
        overwrite=False,
        batch=False,
    )


def test_region_and_slice_configure_match_outputs_to_region_inputs(
    monkeypatch, tmp_path
):
    step_output_paths = [
        str(tmp_path / "build-1" / "part-a" / "region-1" / "micro.vtk"),
        str(tmp_path / "build-1" / "part-a" / "region-2" / "micro.vtk"),
    ]
    solid_outputs = [
        str(tmp_path / "build-1" / "part-a" / "region-1" / "10" / "solid.csv"),
        str(tmp_path / "build-1" / "part-a" / "region-1" / "11" / "solid.csv"),
        str(tmp_path / "build-1" / "part-a" / "region-2" / "12" / "solid.csv"),
    ]
    _configure_workflow_env(monkeypatch, tmp_path, step_output_paths, solid_outputs)

    captured = []

    def capture_setup(case_dir, solid_files, layer_thickness):
        captured.append((case_dir, solid_files, layer_thickness))

    for app_cls in (ExaCAMicrostructureRegion, ExaCAMicrostructureRegionSlice):
        app = app_cls()
        captured.clear()
        monkeypatch.setattr(app, "parse_configure_arguments", lambda: None)
        monkeypatch.setattr(app, "setup_case", capture_setup)
        app.configure()
        assert captured == [
            (
                str(tmp_path / "build-1" / "part-a" / "region-1"),
                sorted(solid_outputs[:2]),
                40.0,
            ),
            (
                str(tmp_path / "build-1" / "part-a" / "region-2"),
                [solid_outputs[2]],
                40.0,
            ),
        ]


def test_region_setup_case_populates_inputs_run_script_and_analysis(
    monkeypatch, tmp_path
):
    _configure_minimal_app_env(monkeypatch, tmp_path)
    material_file = _create_material_root(monkeypatch, tmp_path)
    exe_path, orientation_file = _create_exaca_install(tmp_path)
    solid_file = tmp_path / "solid.csv"
    solid_file.write_text("x,y\n0.0,0.0\n0.00001,0.00002\n", encoding="utf-8")

    template_dir = tmp_path / "template"
    _write_template(template_dir, include_analysis=True)
    case_dir = tmp_path / "case"
    _write_case_metadata(case_dir)

    app = ExaCAMicrostructureRegion()
    app.args = _build_app_args(template_dir, exe_path)
    app.setup_case(str(case_dir), [str(solid_file)], 50.0)

    input_settings = json.loads((case_dir / "inputs.json").read_text(encoding="utf-8"))
    analysis_settings = json.loads(
        (case_dir / "analysis.json").read_text(encoding="utf-8")
    )
    run_script = (case_dir / "runCase.sh").read_text(encoding="utf-8")

    assert input_settings["MaterialFileName"] == str(material_file)
    assert input_settings["GrainOrientationFile"] == str(orientation_file)
    assert input_settings["TemperatureData"]["TemperatureFiles"] == [str(solid_file)]
    assert input_settings["Domain"]["LayerOffset"] == 20.0
    assert "BIN=" in run_script and "EXEC=ExaCA" in run_script
    assert analysis_settings["Regions"]["XY"]["zBounds"] == [16, 16]
    assert analysis_settings["Regions"]["XZ"]["yBounds"] == [4, 4]
    assert analysis_settings["Regions"]["YZ"]["xBounds"] == [2, 2]


def test_slice_setup_case_uses_shared_setup_without_analysis(monkeypatch, tmp_path):
    _configure_minimal_app_env(monkeypatch, tmp_path)
    material_file = _create_material_root(monkeypatch, tmp_path)
    exe_path, orientation_file = _create_exaca_install(tmp_path)
    solid_file = tmp_path / "solid.csv"
    solid_file.write_text("x,y\n0.0,0.0\n", encoding="utf-8")

    template_dir = tmp_path / "template"
    _write_template(template_dir, include_analysis=False)
    case_dir = tmp_path / "case"
    _write_case_metadata(case_dir)

    app = ExaCAMicrostructureRegionSlice()
    app.args = _build_app_args(template_dir, exe_path)
    app.setup_case(str(case_dir), [str(solid_file)], 50.0)

    input_settings = json.loads((case_dir / "inputs.json").read_text(encoding="utf-8"))
    assert input_settings["MaterialFileName"] == str(material_file)
    assert input_settings["GrainOrientationFile"] == str(orientation_file)
    assert not (case_dir / "analysis.json").exists()


def test_region_execute_moves_exaca_vtk_to_workflow_output(monkeypatch, tmp_path):
    _configure_minimal_app_env(monkeypatch, tmp_path)
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    workflow_output = tmp_path / "result.vtk"
    raw_output = case_dir / "exaca.vtk"

    app = ExaCAMicrostructureRegion()
    app.args = SimpleNamespace(overwrite=False, batch=False)
    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: [str(workflow_output)])
    monkeypatch.setattr(app, "get_output_file_status", lambda: ([], [], [False]))
    monkeypatch.setattr(app, "get_case_dirs", lambda output_paths=None: [str(case_dir)])
    monkeypatch.setattr(
        app,
        "run_case",
        lambda case_dir: (
            str(raw_output),
            object(),
        ),
    )
    monkeypatch.setattr(
        app,
        "wait_for_process_success",
        lambda proc: raw_output.write_text("vtk", encoding="utf-8"),
    )

    app.execute()

    assert workflow_output.read_text(encoding="utf-8") == "vtk"


def test_slice_execute_writes_csv_statistics_from_raw_vtk(monkeypatch, tmp_path):
    _configure_minimal_app_env(monkeypatch, tmp_path)
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    workflow_output = case_dir / "slice.csv"
    raw_output = case_dir / "exaca.vtk"
    (case_dir / "inputs.json").write_text(
        json.dumps({"GrainOrientationFile": "orientations.csv"}),
        encoding="utf-8",
    )

    class FakeStructuredPoints:
        def GetSpacing(self):
            return (2.0, 2.0, 2.0)

    class FakeReader:
        def GetOutput(self):
            return FakeStructuredPoints()

    df = pd.DataFrame(
        {
            "X (m)": [0.0, 1.0, 2.0, 3.0],
            "Y (m)": [10.0, 11.0, 12.0, 13.0],
            "Z (m)": [0.0, 1.0, 1.0, 2.0],
        }
    )

    app = ExaCAMicrostructureRegionSlice()
    app.args = SimpleNamespace(overwrite=False, batch=False)
    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: [str(workflow_output)])
    monkeypatch.setattr(app, "get_output_file_status", lambda: ([], [], [False]))
    monkeypatch.setattr(app, "get_case_dirs", lambda output_paths=None: [str(case_dir)])
    monkeypatch.setattr(app, "run_case", lambda case_dir: (str(raw_output), object()))
    monkeypatch.setattr(
        app,
        "wait_for_process_success",
        lambda proc: raw_output.write_text("vtk", encoding="utf-8"),
    )
    monkeypatch.setattr(
        slice_app_module, "grain_id_reader", lambda filepath: FakeReader()
    )
    monkeypatch.setattr(
        slice_app_module, "convert_id_to_rotation", lambda reader, ref_file: df
    )
    monkeypatch.setattr(
        slice_app_module, "get_mean_grain_area", lambda df, spacing: 9.5
    )
    monkeypatch.setattr(slice_app_module, "get_fract_nucleated_grains", lambda df: 0.25)
    monkeypatch.setattr(
        slice_app_module,
        "get_wasserstein_distance_misorientation_z",
        lambda df, ref_file: 1.75,
    )

    app.execute()

    written = pd.read_csv(workflow_output)
    assert written["Z (m)"].tolist() == [1.0, 1.0]
    assert written["Mean Grain Area (m^2)"].tolist() == [9.5, 9.5]
    assert written["Nulceated Fraction"].tolist() == [0.25, 0.25]


def test_slice_postprocess_colors_raw_exaca_vtk(monkeypatch, tmp_path):
    _configure_minimal_app_env(monkeypatch, tmp_path)
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    workflow_output = case_dir / "slice.csv"
    workflow_output.write_text("X (m)\n0.0\n", encoding="utf-8")
    (case_dir / "inputs.json").write_text(
        json.dumps(
            {
                "GrainOrientationFile": "orientations.csv",
                "Printing": {"PathToOutput": "./output", "OutputFile": "exaca"},
            }
        ),
        encoding="utf-8",
    )

    calls = {}
    app = ExaCAMicrostructureRegionSlice()
    monkeypatch.setattr(app, "parse_postprocess_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: [str(workflow_output)])
    monkeypatch.setattr(
        app, "get_output_file_status", lambda: ([str(workflow_output)], [True], [True])
    )
    monkeypatch.setattr(
        slice_app_module,
        "add_rgb_to_vtk",
        lambda in_file, out_file, ref_file: calls.update(
            {"in_file": in_file, "out_file": out_file, "ref_file": ref_file}
        ),
    )

    app.postprocess()

    assert os.path.normpath(calls["in_file"]) == os.path.normpath(
        str(case_dir / "output" / "exaca.vtk")
    )
    assert os.path.normpath(calls["out_file"]) == os.path.normpath(
        str(case_dir / "output" / "exaca_rgb.vtk")
    )
    assert calls["ref_file"] == "orientations.csv"
