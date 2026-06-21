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
import polars as pl
import pytest

from myna.application.thesis import read_parameter
from myna.application.thesis.melt_pool_geometry_part import ThesisMeltPoolGeometryPart
from myna.application.thesis.solidification_build_region import (
    ThesisSolidificationBuildRegion,
)
from myna.application.thesis.solidification_part import ThesisSolidificationPart
from myna.application.thesis.temperature_part import ThesisTemperaturePart
import myna.application.thesis.melt_pool_geometry_part.app as melt_pool_app_module
import myna.application.thesis.thesis as thesis_module


def _build_thesis_step(step_name, class_name=None):
    return {
        step_name: {
            "class": step_name if class_name is None else class_name,
            "application": "thesis",
        }
    }


def _write_settings(
    tmp_path, step_name, step_output_paths, *, steps=None, output_paths=None
):
    steps = [_build_thesis_step(step_name)] if steps is None else steps
    output_paths = (
        {step_name: step_output_paths} if output_paths is None else output_paths
    )
    settings = {
        "steps": steps,
        "data": {
            "build": {
                "build_data": {
                    "material": {"value": "SS316"},
                    "preheat": {"value": 450.0},
                    "print_order": {"value": ["part-b", "part-a", "part-c"]},
                },
                "parts": {},
                "build_regions": {},
            },
            "output_paths": output_paths,
        },
        "myna": {},
    }
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(settings), encoding="utf-8")
    return input_file


def _configure_workflow_env(
    monkeypatch,
    tmp_path,
    step_name,
    step_output_paths=None,
    *,
    workflow_steps=None,
    output_paths=None,
):
    step_output_paths = [] if step_output_paths is None else step_output_paths
    input_file = _write_settings(
        tmp_path,
        step_name,
        step_output_paths,
        steps=workflow_steps,
        output_paths=output_paths,
    )
    monkeypatch.setenv("MYNA_INPUT", str(input_file))
    monkeypatch.setenv("MYNA_STEP_NAME", step_name)
    monkeypatch.delenv("MYNA_LAST_STEP_NAME", raising=False)


def _write_template(template_dir):
    template_dir.mkdir(parents=True)
    template_files = {
        "Beam.txt": "\tWidth_X\t0\n\tWidth_Y\t0\n\tPower\t0\n\tEfficiency\t0\n",
        "Domain.txt": "\tRes\t0\n",
        "Material.txt": "\tT_0\t0\n",
        "Mode.txt": "\tTimes\tunset\n",
        "Output.txt": "\tOutput\t0\n",
        "ParamInput.txt": "\tName\tthermal_3dthesis\n",
        "Path.txt": "X(mm)\tY(mm)\tMode\tPmod\ttParam\n",
        "Settings.txt": "\tMaxThreads\t1\n",
    }
    for name, contents in template_files.items():
        (template_dir / name).write_text(contents, encoding="utf-8")


def _write_scanfile(scanfile, rows=None):
    rows = rows or [
        "0\t0\t1\t0\t0.0",
        "1\t0\t0\t1\t0.002",
        "1\t1\t0\t1\t0.002",
    ]
    scanfile.write_text(
        "X(mm)\tY(mm)\tMode\tPmod\ttParam\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )


def _write_case_metadata(case_dir, payload):
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "myna_data.yaml").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def _build_part_case_payload(scanfile, *, part="part-a", layer="layer-1"):
    return {
        "build": {
            "parts": {
                part: {
                    "laser_power": {"value": 200.0},
                    "spot_size": {"value": 100.0, "unit": "um"},
                    "layer_data": {
                        layer: {
                            "scanpath": {"file_local": str(scanfile)},
                        }
                    },
                }
            },
            "build_data": {
                "material": {"value": "SS316"},
                "preheat": {"value": 450.0},
            },
        }
    }


def _build_region_case_payload(scanfile_a, scanfile_b):
    return {
        "build": {
            "build_regions": {
                "region-1": {
                    "partlist": ["part-a", "part-b"],
                    "parts": {
                        "part-a": {
                            "laser_power": {"value": 220.0},
                            "spot_size": {"value": 80.0, "unit": "um"},
                            "layer_data": {
                                "layer-1": {
                                    "scanpath": {"file_local": str(scanfile_a)},
                                }
                            },
                        },
                        "part-b": {
                            "laser_power": {"value": 250.0},
                            "spot_size": {"value": 0.12, "unit": "mm"},
                            "layer_data": {
                                "layer-1": {
                                    "scanpath": {"file_local": str(scanfile_b)},
                                }
                            },
                        },
                    },
                }
            },
            "build_data": {
                "material": {"value": "SS316"},
                "preheat": {"value": 425.0},
                "print_order": {"value": ["part-c", "part-b", "part-a"]},
            },
        }
    }


def _build_args(template_dir, *, overwrite=False, nout=4, batch=False):
    return SimpleNamespace(
        template=str(template_dir),
        overwrite=overwrite,
        res=12.5e-6,
        nout=nout,
        np=3,
        batch=batch,
        exec="3DThesis",
        initial_temperature_file=None,
        auto_initial_temperature=True,
    )


def _write_temperature_surface_output_case(
    case_dir,
    scanfile,
    temperatures,
    *,
    part="part-a",
    layer="layer-1",
    filename="temperature_surface.csv",
    initial_temperature=450.0,
):
    output_path = case_dir / filename
    _write_case_metadata(
        case_dir,
        _build_part_case_payload(scanfile, part=part, layer=layer),
    )
    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "Material.txt").write_text(
        f"\tT_0\t{initial_temperature}\n",
        encoding="utf-8",
    )
    pd.DataFrame({"T (K)": temperatures}).to_csv(output_path, index=False)
    return output_path


def _patch_material_information(monkeypatch, laser_absorption=0.35):
    class FakeMaterialInformation:
        def __init__(self, path):
            self.path = path

        def write_3dthesis_input(self, output_file):
            with open(output_file, "w", encoding="utf-8") as f:
                f.write("\tT_0\t0\n")

        def get_property(self, name, *_args):
            if name == "laser_absorption":
                return laser_absorption
            return None

    monkeypatch.setattr(
        thesis_module.mist.core,
        "MaterialInformation",
        FakeMaterialInformation,
    )


def test_temperature_and_solidification_part_setup_share_case_configuration(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "temperature_part")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    template_dir = tmp_path / "template"
    _write_template(template_dir)

    case_payload = _build_part_case_payload(scanfile)
    temperature_case = tmp_path / "temperature-case"
    solidification_case = tmp_path / "solidification-case"
    _write_case_metadata(temperature_case, case_payload)
    _write_case_metadata(solidification_case, case_payload)

    temperature_app = ThesisTemperaturePart()
    temperature_app.args = _build_args(template_dir, nout=5)
    temperature_app.configure_case(str(temperature_case))

    solidification_app = ThesisSolidificationPart()
    solidification_app.args = _build_args(template_dir, nout=5)
    solidification_app.configure_case(str(solidification_case))

    for case_dir in (temperature_case, solidification_case):
        assert (case_dir / "Path.txt").read_text(
            encoding="utf-8"
        ) == scanfile.read_text(encoding="utf-8")
        assert read_parameter(str(case_dir / "Beam.txt"), "Power") == ["200.0"]
        assert read_parameter(str(case_dir / "Material.txt"), "T_0") == ["450.0"]
        assert read_parameter(str(case_dir / "Domain.txt"), "Res") == ["1.25e-05"]

    temperature_times = read_parameter(str(temperature_case / "Mode.txt"), "Times")[0]
    solidification_times = read_parameter(
        str(solidification_case / "Mode.txt"), "Times"
    )[0]
    assert temperature_times != "unset"
    assert len([x for x in temperature_times.split(",") if x != ""]) == 5
    assert solidification_times == "unset"
    assert read_parameter(str(temperature_case / "Beam.txt"), "Efficiency") == ["0.35"]


def test_temperature_part_configure_uses_latest_prior_temperature_surface_t0(
    monkeypatch, tmp_path
):
    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    prior_old_case = tmp_path / "surface-old-case"
    prior_new_case = tmp_path / "surface-new-case"
    current_case = tmp_path / "temperature-case"
    prior_old_output = _write_temperature_surface_output_case(
        prior_old_case,
        scanfile,
        [300.0, 350.0],
        initial_temperature=320.0,
    )
    prior_new_output = _write_temperature_surface_output_case(
        prior_new_case,
        scanfile,
        [500.0, 600.0],
        initial_temperature=515.0,
    )
    workflow_steps = [
        _build_thesis_step("surface-old", "temperature_surface_part"),
        _build_thesis_step("surface-new", "temperature_surface_part"),
        _build_thesis_step("temperature_part"),
    ]
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "temperature_part",
        workflow_steps=workflow_steps,
        output_paths={
            "surface-old": [str(prior_old_output)],
            "surface-new": [str(prior_new_output)],
            "temperature_part": [],
        },
    )
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    template_dir = tmp_path / "template"
    _write_template(template_dir)
    _write_case_metadata(current_case, _build_part_case_payload(scanfile))

    app = ThesisTemperaturePart()
    app.args = _build_args(template_dir)
    app.configure_case(str(current_case))

    assert float(read_parameter(str(current_case / "Material.txt"), "T_0")[0]) == (
        pytest.approx(515.0)
    )


def test_solidification_part_configure_uses_manual_initial_temperature_without_match(
    monkeypatch, tmp_path
):
    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    prior_case = tmp_path / "surface-case"
    current_case = tmp_path / "solidification-case"
    prior_output = _write_temperature_surface_output_case(
        prior_case,
        scanfile,
        [700.0, 800.0],
        part="part-b",
    )
    workflow_steps = [
        _build_thesis_step("surface", "temperature_surface_part"),
        _build_thesis_step("solidification_part"),
    ]
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "solidification_part",
        workflow_steps=workflow_steps,
        output_paths={
            "surface": [str(prior_output)],
            "solidification_part": [],
        },
    )
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    template_dir = tmp_path / "template"
    _write_template(template_dir)
    _write_case_metadata(current_case, _build_part_case_payload(scanfile))
    initial_temperature_file = tmp_path / "initial_temperatures.csv"
    initial_temperature_file.write_text(
        "layer,T_0 (K)\n1,525.0\n",
        encoding="utf-8",
    )

    app = ThesisSolidificationPart()
    app.args = _build_args(template_dir)
    app.args.initial_temperature_file = str(initial_temperature_file)
    app.configure_case(str(current_case))

    assert float(read_parameter(str(current_case / "Material.txt"), "T_0")[0]) == (
        pytest.approx(525.0)
    )


def test_temperature_part_configure_uses_preheat_when_auto_initial_temperature_disabled(
    monkeypatch, tmp_path
):
    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    prior_case = tmp_path / "surface-case"
    current_case = tmp_path / "temperature-case"
    prior_output = _write_temperature_surface_output_case(
        prior_case,
        scanfile,
        [500.0, 600.0],
    )
    workflow_steps = [
        _build_thesis_step("surface", "temperature_surface_part"),
        _build_thesis_step("temperature_part"),
    ]
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "temperature_part",
        workflow_steps=workflow_steps,
        output_paths={
            "surface": [str(prior_output)],
            "temperature_part": [],
        },
    )
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    template_dir = tmp_path / "template"
    _write_template(template_dir)
    _write_case_metadata(current_case, _build_part_case_payload(scanfile))
    initial_temperature_file = tmp_path / "initial_temperatures.csv"
    initial_temperature_file.write_text(
        "layer,T_0 (K)\n1,525.0\n",
        encoding="utf-8",
    )

    app = ThesisTemperaturePart()
    app.args = _build_args(template_dir)
    app.args.initial_temperature_file = str(initial_temperature_file)
    app.args.auto_initial_temperature = False
    app.configure_case(str(current_case))

    assert float(read_parameter(str(current_case / "Material.txt"), "T_0")[0]) == (
        pytest.approx(450.0)
    )


def test_temperature_part_configure_falls_back_to_preheat_without_prior_or_csv_match(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "temperature_part")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    template_dir = tmp_path / "template"
    _write_template(template_dir)
    current_case = tmp_path / "temperature-case"
    _write_case_metadata(current_case, _build_part_case_payload(scanfile))
    initial_temperature_file = tmp_path / "initial_temperatures.csv"
    initial_temperature_file.write_text(
        "layer,T_0 (K)\n2,610.0\n",
        encoding="utf-8",
    )

    app = ThesisTemperaturePart()
    app.args = _build_args(template_dir)
    app.args.initial_temperature_file = str(initial_temperature_file)
    app.configure_case(str(current_case))

    assert float(read_parameter(str(current_case / "Material.txt"), "T_0")[0]) == (
        pytest.approx(450.0)
    )


def test_temperature_part_configure_rejects_malformed_initial_temperature_file(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "temperature_part")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    template_dir = tmp_path / "template"
    _write_template(template_dir)
    current_case = tmp_path / "temperature-case"
    _write_case_metadata(current_case, _build_part_case_payload(scanfile))
    initial_temperature_file = tmp_path / "initial_temperatures.csv"
    initial_temperature_file.write_text(
        "layer,temperature\n1,610.0\n",
        encoding="utf-8",
    )

    app = ThesisTemperaturePart()
    app.args = _build_args(template_dir)
    app.args.initial_temperature_file = str(initial_temperature_file)

    with pytest.raises(
        ValueError, match='must contain columns "layer" and "T_0 \\(K\\)"'
    ):
        app.configure_case(str(current_case))


def test_solidification_build_region_configure_creates_ordered_paths_and_beams(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "solidification_build_region")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile_a = tmp_path / "scan_a.txt"
    scanfile_b = tmp_path / "scan_b.txt"
    _write_scanfile(scanfile_a)
    _write_scanfile(scanfile_b, rows=["0\t0\t1\t0\t0.0", "0\t2\t0\t1\t0.004"])
    template_dir = tmp_path / "template"
    _write_template(template_dir)

    case_dir = tmp_path / "case"
    _write_case_metadata(case_dir, _build_region_case_payload(scanfile_a, scanfile_b))

    app = ThesisSolidificationBuildRegion()
    app.args = _build_args(template_dir)
    app.configure_case(str(case_dir))

    assert not (case_dir / "Beam.txt").exists()
    assert (case_dir / "Path_1.txt").exists()
    assert (case_dir / "Path_2.txt").exists()
    assert (case_dir / "Beam_1.txt").exists()
    assert (case_dir / "Beam_2.txt").exists()

    df_path_1 = pl.read_csv(case_dir / "Path_1.txt", separator="\t")
    df_path_2 = pl.read_csv(case_dir / "Path_2.txt", separator="\t")
    assert df_path_1.row(0, named=True)["tParam"] == 0.0
    assert df_path_2.row(0, named=True)["tParam"] > 0.0
    assert read_parameter(str(case_dir / "Material.txt"), "T_0") == ["425.0"]
    assert read_parameter(str(case_dir / "Domain.txt"), "Res") == ["1.25e-05"]


def test_melt_pool_geometry_configure_creates_segment_cases(monkeypatch, tmp_path):
    _configure_workflow_env(monkeypatch, tmp_path, "melt_pool_geometry_part")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    template_dir = tmp_path / "template"
    _write_template(template_dir)

    case_dir = tmp_path / "case"
    _write_case_metadata(case_dir, _build_part_case_payload(scanfile))

    class FakeScanpath:
        def __init__(self, _path, _part, _layer):
            self.file_local = str(scanfile)

        def get_constant_z_slice_indices(self):
            return (
                [(0, 1), (2, 3)],
                pl.DataFrame(
                    {
                        "X(mm)": [0.0, 1.0, 2.0, 3.0],
                        "Y(mm)": [0.0, 0.0, 1.0, 1.0],
                        "Mode": [1, 0, 0, 0],
                        "Pmod": [0, 1, 1, 1],
                        "tParam": [0.0, 0.002, 0.002, 0.002],
                    }
                ),
            )

    class FakeThesisPath:
        def loadData(self, _file):
            return None

        def get_all_scan_stats(self):
            return (10.0, 0.0, 1.0, 1.0)

    monkeypatch.setattr(melt_pool_app_module, "Scanpath", FakeScanpath)
    monkeypatch.setattr(melt_pool_app_module, "ThesisPath", FakeThesisPath)

    app = ThesisMeltPoolGeometryPart()
    app.args = _build_args(template_dir, nout=5)
    app.configure_case(str(case_dir))

    segment_0 = case_dir / "path_segment_000"
    segment_1 = case_dir / "path_segment_001"
    assert segment_0.is_dir()
    assert segment_1.is_dir()
    assert (segment_0 / "Path.txt").exists()
    assert (segment_1 / "Path.txt").exists()
    assert (
        len(
            [
                x
                for x in read_parameter(str(segment_0 / "Mode.txt"), "Times")[0].split(
                    ","
                )
                if x
            ]
        )
        == 2
    )
    assert (
        len(
            [
                x
                for x in read_parameter(str(segment_1 / "Mode.txt"), "Times")[0].split(
                    ","
                )
                if x
            ]
        )
        == 3
    )


def test_melt_pool_geometry_segments_inherit_resolved_initial_temperature(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "melt_pool_geometry_part")
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(tmp_path / "install"))
    _patch_material_information(monkeypatch)

    scanfile = tmp_path / "scan.txt"
    _write_scanfile(scanfile)
    template_dir = tmp_path / "template"
    _write_template(template_dir)
    initial_temperature_file = tmp_path / "initial_temperatures.csv"
    initial_temperature_file.write_text(
        "layer,T_0 (K)\n1,610.0\n",
        encoding="utf-8",
    )

    case_dir = tmp_path / "case"
    _write_case_metadata(case_dir, _build_part_case_payload(scanfile))

    class FakeScanpath:
        def __init__(self, _path, _part, _layer):
            self.file_local = str(scanfile)

        def get_constant_z_slice_indices(self):
            return (
                [(0, 1), (2, 3)],
                pl.DataFrame(
                    {
                        "X(mm)": [0.0, 1.0, 2.0, 3.0],
                        "Y(mm)": [0.0, 0.0, 1.0, 1.0],
                        "Mode": [1, 0, 0, 0],
                        "Pmod": [0, 1, 1, 1],
                        "tParam": [0.0, 0.002, 0.002, 0.002],
                    }
                ),
            )

    class FakeThesisPath:
        def loadData(self, _file):
            return None

        def get_all_scan_stats(self):
            return (10.0, 0.0, 1.0, 1.0)

    monkeypatch.setattr(melt_pool_app_module, "Scanpath", FakeScanpath)
    monkeypatch.setattr(melt_pool_app_module, "ThesisPath", FakeThesisPath)

    app = ThesisMeltPoolGeometryPart()
    app.args = _build_args(template_dir, nout=5)
    app.args.initial_temperature_file = str(initial_temperature_file)
    app.configure_case(str(case_dir))

    assert float(read_parameter(str(case_dir / "Material.txt"), "T_0")[0]) == (
        pytest.approx(610.0)
    )
    assert float(
        read_parameter(str(case_dir / "path_segment_000" / "Material.txt"), "T_0")[0]
    ) == pytest.approx(610.0)
    assert float(
        read_parameter(str(case_dir / "path_segment_001" / "Material.txt"), "T_0")[0]
    ) == pytest.approx(610.0)


def test_temperature_execute_exports_snapshot_schema(monkeypatch, tmp_path):
    output_path = tmp_path / "temperature.csv"
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "temperature_part",
        [str(output_path)],
    )

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    result_file = case_dir / "Data" / "thermal_3dthesis.Snapshot.3.csv"
    result_file.parent.mkdir()
    result_file.write_text(
        "x,y,z,T\n0.1,0.2,0.3,1200\n",
        encoding="utf-8",
    )

    app = ThesisTemperaturePart()
    app.args = _build_args(tmp_path / "unused", nout=4)
    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: [str(output_path)])
    monkeypatch.setattr(app, "get_case_dirs", lambda output_paths=None: [str(case_dir)])
    monkeypatch.setattr(
        app, "run_case", lambda proc_list: [str(result_file), proc_list]
    )

    app.execute()

    written = pd.read_csv(output_path)
    assert list(written.columns) == ["x (m)", "y (m)", "z (m)", "T (K)"]
    assert written.iloc[0].to_dict() == {
        "x (m)": 0.1,
        "y (m)": 0.2,
        "z (m)": 0.3,
        "T (K)": 1200.0,
    }


def test_solidification_part_execute_merges_final_csvs(monkeypatch, tmp_path):
    case_dir = tmp_path / "case"
    output_path = case_dir / "solidification.csv"
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "solidification_part",
        [str(output_path)],
    )

    data_dir = case_dir / "Data"
    data_dir.mkdir(parents=True)
    (case_dir / "ParamInput.txt").write_text(
        "\tName\tthermal_3dthesis\n", encoding="utf-8"
    )
    (data_dir / "thermal_3dthesis.Solidification.Final.0.csv").write_text(
        "x,y,G,V\n0.0,1.0,2.0,3.0\n",
        encoding="utf-8",
    )
    (data_dir / "thermal_3dthesis.Solidification.Final.1.csv").write_text(
        "x,y,G,V\n4.0,5.0,6.0,7.0\n",
        encoding="utf-8",
    )

    app = ThesisSolidificationPart()
    app.args = _build_args(tmp_path / "unused")
    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "run_case", lambda proc_list: proc_list)

    app.execute()

    written = pd.read_csv(output_path)
    assert list(written.columns) == ["x (m)", "y (m)", "G (K/m)", "V (m/s)"]
    assert written.shape == (2, 4)
    assert written["G (K/m)"].tolist() == [2.0, 6.0]


def test_solidification_build_region_execute_exports_single_final_csv(
    monkeypatch, tmp_path
):
    output_path = tmp_path / "build-region.csv"
    _configure_workflow_env(
        monkeypatch,
        tmp_path,
        "solidification_build_region",
        [str(output_path)],
    )

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    result_file = case_dir / "Data" / "thermal_3dthesis.Solidification.Final.csv"
    result_file.parent.mkdir()
    result_file.write_text(
        "x,y,G,V\n0.1,0.2,0.3,0.4\n",
        encoding="utf-8",
    )

    app = ThesisSolidificationBuildRegion()
    app.args = _build_args(tmp_path / "unused")
    monkeypatch.setattr(app, "parse_execute_arguments", lambda: None)
    monkeypatch.setattr(app, "get_step_output_paths", lambda: [str(output_path)])
    monkeypatch.setattr(app, "get_case_dirs", lambda output_paths=None: [str(case_dir)])
    monkeypatch.setattr(
        app, "run_case", lambda proc_list: [str(result_file), proc_list]
    )

    app.execute()

    written = pd.read_csv(output_path)
    assert list(written.columns) == ["x (m)", "y (m)", "G (K/m)", "V (m/s)"]
    assert written.iloc[0].to_dict() == {
        "x (m)": 0.1,
        "y (m)": 0.2,
        "G (K/m)": 0.3,
        "V (m/s)": 0.4,
    }


def test_temperature_run_case_reuses_existing_results_unless_overwriting(
    monkeypatch, tmp_path
):
    _configure_workflow_env(monkeypatch, tmp_path, "temperature_part")

    case_dir = tmp_path / "case"
    data_dir = case_dir / "Data"
    data_dir.mkdir(parents=True)
    (case_dir / "ParamInput.txt").write_text(
        "\tName\tthermal_3dthesis\n", encoding="utf-8"
    )
    (case_dir / "Settings.txt").write_text("\tMaxThreads\t1\n", encoding="utf-8")
    existing_file = data_dir / "existing.csv"
    existing_file.write_text("x,y,z,T\n", encoding="utf-8")

    app = ThesisTemperaturePart()
    app.args = _build_args(tmp_path / "unused", overwrite=False, nout=4)
    app.set_case(str(case_dir), str(case_dir))
    monkeypatch.setattr(
        app,
        "run_thesis_case",
        lambda *_args: (_ for _ in ()).throw(AssertionError("case should be skipped")),
    )

    result_file, proc_list = app.run_case([])

    assert result_file == str(existing_file)
    assert proc_list == []
    assert read_parameter(str(case_dir / "Settings.txt"), "MaxThreads") == ["3"]

    app.args = _build_args(tmp_path / "unused", overwrite=True, nout=4)
    monkeypatch.setattr(
        app, "run_thesis_case", lambda _case_dir, procs: procs + ["ran"]
    )

    result_file, proc_list = app.run_case([])

    assert result_file.endswith("thermal_3dthesis.Snapshot.3.csv")
    assert proc_list == ["ran"]
