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


@pytest.mark.examples
def test_solidification_part():
    """This checks the solidification_part example"""
    with working_directory(get_example_dir("solidification_part")):
        output = subprocess.run(
            get_run_cmd_str(),
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output


@pytest.mark.examples
def test_solidification_part_hdf5():
    """This checks the solidification_part example"""
    with working_directory(get_example_dir("solidification_part_hdf5")):
        output = subprocess.run(
            get_run_cmd_str(),
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output


@pytest.mark.examples
def test_solidification_part_json():
    """This checks the solidification_part example"""
    with working_directory(get_example_dir("solidification_part_json")):
        output = subprocess.run(
            get_run_cmd_str(),
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output
