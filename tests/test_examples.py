#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil
import pytest
from myna.core.utils import working_directory
from myna.core.workflow.config import config
from myna.core.workflow.run import run


def get_example_dir(example_name):
    """Creates a temporary directory for running the example"""
    test_path = os.path.dirname(os.path.abspath(__file__))
    myna_path = os.path.abspath(os.path.join(test_path, ".."))
    return os.path.join(myna_path, "examples", example_name)


def run_example_test(example_name):
    """Perform a test run of the example case in a temporary directory, then clean up"""

    # Setup the temporary directory for the example to run.
    # The `tmp` directories need to be in `examples/` to find the database files.
    example_dir = get_example_dir(example_name)
    tmp_dir = example_dir + "_tmp"
    os.makedirs(tmp_dir)
    shutil.copyfile(
        os.path.join(example_dir, "input.yaml"), os.path.join(tmp_dir, "input.yaml")
    )

    # Run and clean the example
    with working_directory(tmp_dir):
        config("input.yaml")
        run("input.yaml")
        shutil.rmtree(tmp_dir, ignore_errors=True)


def get_run_cmd_str():
    """Returns a command string to launch and clean an example case. Assumes a clean
    directory to begin with"""
    return (
        "myna config --output ic.yaml"
        + " && myna run --input ic.yaml"
        + " && rm -rf myna_output myna_resources ic.yaml"
    )


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
