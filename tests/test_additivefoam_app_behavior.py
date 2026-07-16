#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import sys
from pathlib import Path

from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam import additivefoam as additivefoam_module
from myna.application.additivefoam.solidification_region_reduced import (
    AdditiveFOAMRegionReduced,
)
from myna.application.additivefoam.solidification_region_reduced import (
    app as reduced_app,
)


def test_region_reduced_custom_heatsourcedict_overwrites_template_before_updates(
    monkeypatch, tmp_path
):
    custom_heat_source = tmp_path / "customHeatSourceDict"
    custom_heat_source.write_text("custom heat source\n", encoding="utf-8")

    case_dir = tmp_path / "case"
    constant_dir = case_dir / "constant"
    constant_dir.mkdir(parents=True)
    (constant_dir / "heatSourceDict").write_text(
        "template heat source\n", encoding="utf-8"
    )

    scanpath_source = tmp_path / "scanpath.txt"
    scanpath_source.write_text("scan data\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["test", "--custom-heatsourcedict", str(custom_heat_source)],
    )
    monkeypatch.setattr(AdditiveFOAM, "validate_executable", lambda self, default: None)
    app = AdditiveFOAMRegionReduced()
    app.parse_configure_arguments()
    app.settings = {
        "data": {
            "build": {
                "parts": {
                    "partA": {
                        "laser_power": {"value": 250.0},
                    }
                }
            }
        }
    }

    calls = []

    def fake_convert(src, dst, power):
        Path(dst).write_text(
            f"copied from {Path(src).name} at {power}\n", encoding="utf-8"
        )

    def fake_update_beam(part, working_case_dir):
        calls.append(("beam", part))
        assert (
            Path(working_case_dir, "constant", "heatSourceDict").read_text(
                encoding="utf-8"
            )
            == "custom heat source\n"
        )
        Path(working_case_dir, "constant", "heatSourceDict").write_text(
            "custom heat source\nbeam updated\n", encoding="utf-8"
        )

    def fake_update_material(working_case_dir):
        calls.append(("material", working_case_dir))
        assert (
            Path(working_case_dir, "constant", "heatSourceDict").read_text(
                encoding="utf-8"
            )
            == "custom heat source\nbeam updated\n"
        )

    monkeypatch.setattr(reduced_app, "convert_peregrine_scanpath", fake_convert)
    monkeypatch.setattr(app, "update_beam_spot_size", fake_update_beam)
    monkeypatch.setattr(app, "update_material_properties", fake_update_material)
    monkeypatch.setattr(
        app, "update_region_start_and_end_times", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        app, "update_heatsource_scanfile", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(app, "update_exaca_mesh_size", lambda *_args, **_kwargs: None)

    case_dict = {
        "part": "partA",
        "layer": "1",
        "case_dir": str(case_dir),
        "region_dict": {
            "layer_data": {"1": {"scanpath": {"file_local": str(scanpath_source)}}}
        },
        "rve_mesh_dict": {"bb_dict": {"bb_min": [0, 0], "bb_max": [1, 1]}},
    }

    app.update_case_metadata(case_dict)

    assert calls == [("beam", "partA"), ("material", str(case_dir))]
    assert (
        (constant_dir / "heatSourceDict")
        .read_text(encoding="utf-8")
        .startswith("custom heat source\n")
    )


def test_update_material_properties_preserves_custom_heat_source_absorption(
    monkeypatch, tmp_path
):
    custom_heat_source = tmp_path / "customHeatSourceDict"
    custom_heat_source.write_text("custom heat source\n", encoding="utf-8")

    case_dir = tmp_path / "case"
    constant_dir = case_dir / "constant"
    system_dir = case_dir / "system"
    constant_dir.mkdir(parents=True)
    system_dir.mkdir(parents=True)
    (constant_dir / "transportProperties").write_text("", encoding="utf-8")
    (constant_dir / "thermoPath").write_text("", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        ["test", "--custom-heatsourcedict", str(custom_heat_source)],
    )
    monkeypatch.setattr(AdditiveFOAM, "validate_executable", lambda self, default: None)
    app = AdditiveFOAM()
    app.parse_configure_arguments()
    app.settings = {"data": {"build": {"build_data": {"material": {"value": "IN625"}}}}}

    writes = []

    class FakeMaterialInformation:
        def __init__(self, _material_data):
            pass

        def write_additivefoam_input(self, transport_file, thermo_file):
            Path(transport_file).write_text("transport", encoding="utf-8")
            Path(thermo_file).write_text("thermo", encoding="utf-8")

        def get_property(self, name, *_args):
            if name == "liquidus_temperature":
                return 1700.0
            if name == "laser_absorption":
                return 0.42
            raise AssertionError(f"unexpected material property {name}")

    monkeypatch.setattr(
        additivefoam_module.mist.core,
        "MaterialInformation",
        FakeMaterialInformation,
        raising=False,
    )
    monkeypatch.setattr(
        additivefoam_module.os, "environ", {"MYNA_INSTALL_PATH": str(tmp_path)}
    )
    monkeypatch.setattr(
        additivefoam_module,
        "update_parameter",
        lambda path, key, value: writes.append((path, key, value)),
    )
    monkeypatch.setattr(
        additivefoam_module.subprocess,
        "check_output",
        lambda *_args, **_kwargs: b"gaussian\n",
    )

    app.update_material_properties(str(case_dir))

    assert writes == []
