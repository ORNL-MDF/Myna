#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Behavior tests for the Condor application wrapper."""

import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from myna.application.condor import Condor
from myna.application.condor.solidification_part import CondorSolidificationPart
import myna.core.context as context_module


TEMPLATE_DIR = (
    Path(__file__).parents[1]
    / "src"
    / "myna"
    / "application"
    / "condor"
    / "solidification_part"
    / "template"
)


def _write_json(path, contents):
    path.write_text(json.dumps(contents), encoding="utf-8")


def _case_payload(scanfile):
    return {
        "build": {
            "parts": {
                "part-a": {
                    "laser_power": {"value": 200.0},
                    "spot_size": {"value": 100.0, "unit": "um"},
                    "layer_data": {
                        "layer-1": {"scanpath": {"file_local": str(scanfile)}}
                    },
                }
            },
            "build_data": {
                "material": {"value": "SS316L"},
                "preheat": {"value": 450.0},
            },
        }
    }


def _args(*, overwrite=False, batch=False, executable="condor"):
    return SimpleNamespace(
        template=str(TEMPLATE_DIR),
        overwrite=overwrite,
        res=25e-6,
        np=1,
        maxproc=1,
        batch=batch,
        exec=executable,
        mpiexec=None,
        mpiflags=None,
        env=None,
        docker_image=None,
    )


def test_configure_case_writes_condor_inputs(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["test"])
    monkeypatch.setenv("MYNA_INSTALL_PATH", str(Path(__file__).parents[1] / "src/myna"))
    scanfile = tmp_path / "scan.txt"
    scanfile.write_text(
        "Mode\tX(mm)\tY(mm)\tZ(mm)\tPmod\ttParam\n"
        "1\t0\t0\t0\t0\t0\n"
        "0\t1\t0\t0\t1\t0.5\n",
        encoding="utf-8",
    )
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_json(case_dir / "myna_data.yaml", _case_payload(scanfile))

    app = CondorSolidificationPart(validate_executable=False)
    app.args = _args()
    app.configure_case(case_dir)

    assert (case_dir / "Path.txt").read_text(encoding="utf-8") == scanfile.read_text(
        encoding="utf-8"
    )
    beam = json.loads((case_dir / "Beam.json").read_text(encoding="utf-8"))
    expected_width = 0.25 * math.sqrt(6) * 100e-6
    assert beam["shape"]["width_x"] == pytest.approx(expected_width)
    assert beam["shape"]["width_y"] == pytest.approx(expected_width)
    assert beam["shape"]["depth_z"] == pytest.approx(10e-6)
    assert beam["intensity"] == {"power": 200.0, "efficiency": 0.36}

    material = json.loads((case_dir / "Material.json").read_text(encoding="utf-8"))
    constants = material["constants"]
    assert constants["T_0"] == 450.0
    assert constants["T_L"] == 1709
    assert constants["k"] == pytest.approx(32.35741)
    assert constants["c"] == pytest.approx(582.1959)
    assert constants["p"] == 7955

    domain = json.loads((case_dir / "Domain.json").read_text(encoding="utf-8"))
    assert domain["domain"]["resolution"] == pytest.approx(25e-6)
    settings = json.loads((case_dir / "Settings.json").read_text(encoding="utf-8"))
    assert settings["output"]["dim"] == "2D"
    mode = json.loads((case_dir / "Mode.json").read_text(encoding="utf-8"))
    outputs = mode["Interface"]["hooks"]["solidification"]["outputs"]
    assert outputs["G"] is True
    assert outputs["V"] is True


def test_set_case_preserves_workflow_input(monkeypatch, tmp_path):
    workflow_input = tmp_path / "workflow.yaml"
    workflow_input.write_text("steps: []\n", encoding="utf-8")
    monkeypatch.setenv("MYNA_INPUT", str(workflow_input))
    monkeypatch.setattr(sys, "argv", ["test"])
    monkeypatch.setattr(context_module, "_LEGACY_ENV_FALLBACK_WARNED", False)

    with pytest.warns(DeprecationWarning, match="Myna 2.0"):
        app = Condor(validate_executable=False)
    app.set_case(tmp_path / "case", tmp_path / "output")

    assert app.input_file == str(workflow_input)
    assert app.case_input_file == str(tmp_path / "case" / "ParamInput.json")


def test_export_solidification_results_merges_serial_or_rank_files(tmp_path):
    rank_zero = tmp_path / "thermal_condor.rank0_Final.csv"
    rank_one = tmp_path / "thermal_condor.rank1_Final.csv"
    rank_zero.write_text("x,y,z,G,V\n0,1,2,3,4\n", encoding="utf-8")
    rank_one.write_text("x,y,z,G,V\n5,6,7,8,9\n", encoding="utf-8")
    output = tmp_path / "solidification.csv"

    Condor.export_solidification_results([rank_zero, rank_one], output)

    written = pd.read_csv(output)
    assert list(written) == ["x (m)", "y (m)", "G (K/m)", "V (m/s)"]
    assert written.to_dict("records") == [
        {"x (m)": 0, "y (m)": 1, "G (K/m)": 3, "V (m/s)": 4},
        {"x (m)": 5, "y (m)": 6, "G (K/m)": 8, "V (m/s)": 9},
    ]


def test_export_solidification_results_rejects_missing_data(tmp_path):
    with pytest.raises(FileNotFoundError, match="No Condor final"):
        Condor.export_solidification_results([], tmp_path / "output.csv")

    invalid = tmp_path / "invalid.csv"
    invalid.write_text("x,y,G\n0,1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns: V"):
        Condor.export_solidification_results([invalid], tmp_path / "output.csv")


def test_run_case_skips_or_removes_only_final_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["test"])
    case_dir = tmp_path / "case"
    data_dir = case_dir / "Data"
    data_dir.mkdir(parents=True)
    _write_json(case_dir / "ParamInput.json", {"name": "thermal_condor"})
    final = data_dir / "thermal_condor_Final.csv"
    final.write_text("x,y,G,V\n", encoding="utf-8")
    intermediate = data_dir / "thermal_condor_10.csv"
    intermediate.write_text("x,y,G,V\n", encoding="utf-8")

    app = Condor(validate_executable=False)
    app.args = _args(overwrite=False)
    app.set_case(case_dir, case_dir)
    monkeypatch.setattr(
        app,
        "run_condor_case",
        lambda *_args: (_ for _ in ()).throw(AssertionError("case should skip")),
    )
    assert app.run_case([]) == []
    assert final.exists()

    app.args = _args(overwrite=True)
    monkeypatch.setattr(
        app,
        "run_condor_case",
        lambda _case, processes: processes + ["ran"],
    )
    assert app.run_case([]) == ["ran"]
    assert not final.exists()
    assert intermediate.exists()


def test_run_condor_case_restores_working_directory(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["test"])
    case_dir = tmp_path / "case"
    case_dir.mkdir()
    _write_json(case_dir / "ParamInput.json", {"name": "thermal_condor"})

    app = Condor(validate_executable=False)
    app.args = _args(executable="/bin/true")
    app.set_case(case_dir, case_dir)
    starting_directory = os.getcwd()

    processes = app.run_condor_case(str(case_dir), [])

    assert len(processes) == 1
    assert os.getcwd() == starting_directory
    log = (case_dir / "myna_condor_run.log").read_text(encoding="utf-8")
    assert f"- Working directory: {case_dir}" in log
