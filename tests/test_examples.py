#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for configuring and running example cases. Each example test should be marked
with `@pytest.mark.examples`. By default, it is assumed that each example uses a single
processor. Additional markers should be specified to indicate test complexity:

- @pytest.mark.apps: requires external dependency
- @pytest.mark.parallel: example uses 2 processors instead of 1
"""

import os
import shutil
import pytest
import pandas as pd
from myna.core.utils import working_directory
from myna.core.workflow.load_input import load_input
from myna.core.workflow.config import config
from myna.core.workflow.run import run
from myna.application.thesis import read_parameter

from .example_paths import CASES_DIR


def get_example_dir(example_name):
    """Return the directory for a runnable example case."""
    return CASES_DIR / example_name


def copy_example_to_tmp_dir(example_name):
    """Copy an example input into a temporary case directory under `examples/cases`."""
    example_dir = get_example_dir(example_name)
    tmp_dir = example_dir.parent / f"{example_dir.name}_tmp"
    os.makedirs(tmp_dir)
    shutil.copyfile(example_dir / "input.yaml", tmp_dir / "input.yaml")
    return tmp_dir


def run_example_test(example_name):
    """Perform a test run of the example case in a temporary directory, then clean up"""

    # The `tmp` directories need to be in `examples/cases/` to find the database files.
    tmp_dir = copy_example_to_tmp_dir(example_name)

    # Run and clean the example
    try:
        with working_directory(tmp_dir):
            config("input.yaml")
            run("input.yaml")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.apps
@pytest.mark.examples
def test_solidification_part():
    """This checks the solidification_part example. Estimated runtime ~20s."""
    run_example_test("solidification_part")


@pytest.mark.apps
@pytest.mark.examples
def test_solidification_part_hdf5():
    """This checks the solidification_part example. Estimated runtime ~20s."""
    run_example_test("solidification_part_hdf5")


@pytest.mark.apps
@pytest.mark.examples
def test_solidification_part_json():
    """This checks the solidification_part example. Estimated runtime ~20s."""
    run_example_test("solidification_part_json")


@pytest.mark.apps
@pytest.mark.examples
def test_solidification_part_pelican():
    """This checks the solidification_part Pelican example. Estimated runtime ~20s."""
    run_example_test("solidification_part_pelican")


@pytest.mark.apps
@pytest.mark.examples
def test_melt_pool_geometry_part_pelican():
    """This checks the melt_pool_geometry_part_pelican example. Estimated runtime ~15-30s."""
    run_example_test("melt_pool_geometry_part_pelican")


@pytest.mark.apps
@pytest.mark.examples
def test_temperature_surface_part():
    """This checks the temperature_surface_part example. Estimated runtime ~30-45s."""

    tmp_dir = copy_example_to_tmp_dir("temperature_surface_part")

    try:
        with working_directory(tmp_dir):
            config("input.yaml")
            settings = load_input("input.yaml")
            output_paths = settings["data"]["output_paths"]["3dthesis"]

            case_records = []
            for output_path in output_paths:
                case_dir = os.path.dirname(output_path)
                case_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
                part = list(case_settings["build"]["parts"].keys())[0]
                layer = int(
                    list(case_settings["build"]["parts"][part]["layer_data"].keys())[0]
                )
                case_records.append((layer, case_dir, output_path))
            case_records.sort(key=lambda record: record[0])

            run("input.yaml")

            first_output = case_records[0][2]
            second_output = case_records[1][2]
            second_case_dir = case_records[1][1]

            assert os.path.exists(first_output)
            assert os.path.exists(second_output)
            assert set(pd.read_csv(first_output).columns) == {
                "x (m)",
                "y (m)",
                "z (m)",
                "T (K)",
            }

            average_temperature = pd.read_csv(first_output)["T (K)"].mean()
            second_t0 = float(
                read_parameter(os.path.join(second_case_dir, "Material.txt"), "T_0")[0]
            )
            assert second_t0 == pytest.approx(average_temperature)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.mark.apps
@pytest.mark.examples
@pytest.mark.parallel
def test_microstructure_region():
    """This checks the microstructure_region example, which checks:

        - additivefoam/solidification_region_reduced
        - exaca/microstructure_region

    Estimated runtime ~40s."""
    run_example_test("microstructure_region")


@pytest.mark.apps
@pytest.mark.examples
@pytest.mark.parallel
def test_solidification_region_reduced_stl():
    """This checks the solidification_region_reduced_stl example, which checks:

        - additivefoam/solidification_region_reduced_stl

    Estimated runtime ~40s."""
    run_example_test("solidification_region_reduced_stl")
