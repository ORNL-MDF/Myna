#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pytest
import subprocess
from myna.core.utils import working_directory


def get_example_dir(example_name):
    """Creates a temporary directory for running the example"""
    test_path = os.path.dirname(os.path.abspath(__file__))
    myna_path = os.path.abspath(os.path.join(test_path, ".."))
    return os.path.join(myna_path, "examples", example_name)


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
@pytest.mark.parallel
def test_microstructure_region():
    """This checks the microstructure_region example, which checks:

        - additivefoam/solidification_region_reduced
        - exaca/microstructure_region

    Estimated runtime ~40s."""
    with working_directory(get_example_dir("microstructure_region")):
        output = subprocess.run(
            get_run_cmd_str(),
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output


@pytest.mark.apps
@pytest.mark.examples
@pytest.mark.parallel
def test_solidification_region_reduced_stl():
    """This checks the solidification_region_reduced_stl example, which checks:

        - additivefoam/solidification_region_reduced_stl

    Estimated runtime ~40s."""
    with working_directory(get_example_dir("solidification_region_reduced_stl")):
        output = subprocess.run(
            get_run_cmd_str(),
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output
