#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import argparse
import sys
import os
import shutil
import warnings

import myna
import myna.core.context as context_module
import pytest
import yaml

from myna.core.workflow.load_input import load_input, write_input

from .example_paths import CASES_DIR


# This test checks that all examples can be correctly configured.
def run_configure(example):
    parser = argparse.ArgumentParser("test")

    # Currently required to run from the example folder
    test_dir = os.getcwd()
    example_path = CASES_DIR / example
    os.chdir(example_path)

    # Rely heavily on defaults (modify output to avoid local changes from test)
    output_dir = example_path / "tmp"
    output_file = output_dir / "test.json"
    if not output_dir.exists():
        output_dir.mkdir()
    sys.argv = ["test", "--output", os.fspath(output_file)]
    myna.core.workflow.config.parse(parser)

    # Check if output file was generated
    assert output_file.exists()

    # Cleanup
    shutil.rmtree(output_dir)
    os.chdir(test_dir)


def test_configure():
    context_module._LEGACY_ENV_FALLBACK_WARNED = False
    examples = [
        "cluster_solidification",
        "depth_map_part",
        "melt_pool_geometry_part",
        "melt_pool_geometry_part_heat_accumulation",
        "melt_pool_geometry_part_pelican",
        "microstructure_region",
        "microstructure_region_slice",
        "openfoam_meshing",
        "rve_part_center",
        "solidification_build_region",
        "solidification_part",
        "solidification_part_hdf5",
        "solidification_part_json",
        "solidification_part_pelican",
        "solidification_region_reduced",
        "solidification_region_reduced_stl",
        "temperature_surface_part",
        "temperature_part",
        "temperature_part_pvd",
        "vtk_to_exodus_region",
    ]

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        for example in examples:
            run_configure(example)

    unexpected = [
        warning for warning in record if warning.category is not DeprecationWarning
    ]
    assert unexpected == []


def test_config_writes_relative_runtime_paths_and_absolute_provenance(tmp_path):
    example = "solidification_part_json"
    example_path = CASES_DIR / example
    tmp_dir = tmp_path / example
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    myna.core.workflow.config.config(os.fspath(input_file))

    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))
    output_path = raw_settings["data"]["output_paths"]["3dthesis"][0]
    scanpath = raw_settings["data"]["build"]["parts"]["P5"]["layer_data"]["51"][
        "scanpath"
    ]

    assert not os.path.isabs(output_path)
    assert not os.path.isabs(raw_settings["myna"]["workspace"])
    assert not os.path.isabs(scanpath["file_local"])
    assert os.path.isabs(scanpath["file_database"])
    assert os.path.isabs(raw_settings["data"]["build"]["path"])

    case_dir = tmp_dir / os.path.dirname(output_path)
    case_raw = yaml.safe_load((case_dir / "myna_data.yaml").read_text(encoding="utf-8"))
    case_scanpath = case_raw["build"]["parts"]["P5"]["layer_data"]["51"]["scanpath"]

    assert not os.path.isabs(case_scanpath["file_local"])
    assert os.path.isabs(case_scanpath["file_database"])
    assert (case_dir / case_scanpath["file_local"]).resolve() == (
        tmp_dir / "myna_resources" / "P5" / "51" / "scanpath.txt"
    ).resolve()

    loaded_settings = load_input(input_file)
    assert os.path.isabs(loaded_settings["myna"]["workspace"])
    assert os.path.isabs(loaded_settings["data"]["build"]["path"])
    assert os.path.isabs(loaded_settings["data"]["output_paths"]["3dthesis"][0])
    assert os.path.isabs(
        loaded_settings["data"]["build"]["parts"]["P5"]["layer_data"]["51"]["scanpath"][
            "file_local"
        ]
    )


def test_config_expands_layer_range_strings_in_written_input(tmp_path):
    example = "solidification_part_json"
    example_path = CASES_DIR / example
    tmp_dir = tmp_path / example
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    source_settings["data"]["build"]["parts"]["P5"]["layers"] = "51-52"

    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    myna.core.workflow.config.config(os.fspath(input_file))

    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))

    assert raw_settings["data"]["build"]["parts"]["P5"]["layers"] == [51, 52]
    assert sorted(
        int(layer)
        for layer in raw_settings["data"]["build"]["parts"]["P5"]["layer_data"].keys()
    ) == [51, 52]
    assert len(raw_settings["data"]["output_paths"]["3dthesis"]) == 2


def test_config_missing_part_layer_fails_without_ignore_flag(tmp_path):
    example_path = CASES_DIR / "solidification_part_json"
    tmp_dir = tmp_path / "solidification_part_json"
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    source_settings["data"]["build"]["parts"]["P5"]["layers"] = [51, 999]

    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    with pytest.raises(KeyError):
        myna.core.workflow.config.config(os.fspath(input_file))


def test_config_ignore_missing_part_layers_skips_missing_cases(tmp_path):
    example_path = CASES_DIR / "solidification_part_json"
    tmp_dir = tmp_path / "solidification_part_json"
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    source_settings["myna"]["ignore_missing_layers"] = True
    source_settings["data"]["build"]["parts"]["P5"]["layers"] = [51, 999]

    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    myna.core.workflow.config.config(os.fspath(input_file))

    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))

    assert raw_settings["myna"]["ignore_missing_layers"] is True
    assert raw_settings["data"]["build"]["parts"]["P5"]["layers"] == [51]
    assert sorted(
        int(layer)
        for layer in raw_settings["data"]["build"]["parts"]["P5"]["layer_data"].keys()
    ) == [51]
    assert len(raw_settings["data"]["output_paths"]["3dthesis"]) == 1
    assert "/999/" not in raw_settings["data"]["output_paths"]["3dthesis"][0]


def test_config_ignore_missing_build_region_layers_skips_missing_cases(tmp_path):
    example_path = CASES_DIR / "solidification_build_region"
    tmp_dir = tmp_path / "solidification_build_region"
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    source_settings["steps"] = [source_settings["steps"][0]]
    source_settings["myna"]["ignore_missing_layers"] = True
    source_settings["data"]["build"]["build_regions"] = {
        "test_1": {"partlist": ["P5"], "layerlist": [51, 999]}
    }
    source_settings["data"]["build"]["parts"] = {"P5": {"layers": [51]}}

    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    myna.core.workflow.config.config(os.fspath(input_file))

    raw_settings = yaml.safe_load(input_file.read_text(encoding="utf-8"))

    assert raw_settings["data"]["build"]["build_regions"]["test_1"]["layerlist"] == [51]
    assert sorted(
        int(layer)
        for layer in raw_settings["data"]["build"]["build_regions"]["test_1"]["parts"][
            "P5"
        ]["layer_data"].keys()
    ) == [51]
    assert len(raw_settings["data"]["output_paths"]["3dthesis"]) == 1


def test_config_ignore_missing_layers_still_fails_for_region_steps(tmp_path):
    example_path = CASES_DIR / "solidification_part_json"
    tmp_dir = tmp_path / "solidification_region_json"
    tmp_dir.mkdir()

    source_settings = load_input(example_path / "input.yaml")
    source_settings["myna"]["ignore_missing_layers"] = True
    source_settings["steps"] = [
        {
            "additivefoam": {
                "class": "solidification_region_reduced",
                "application": "additivefoam",
            }
        }
    ]
    source_settings["data"]["build"]["parts"] = {
        "P5": {"regions": {"r1": {"layers": [51, 999], "x": 0.2, "y": 0.021}}}
    }

    input_file = tmp_dir / "input.yaml"
    write_input(source_settings, input_file)

    with pytest.raises(KeyError):
        myna.core.workflow.config.config(os.fspath(input_file))
