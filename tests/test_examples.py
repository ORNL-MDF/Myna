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


@pytest.mark.examples
def test_solidification():
    """This checks the solidification_part example"""
    with working_directory(get_example_dir("solidification_part")):
        output = subprocess.run(
            "myna config --output ic.yaml"
            + " && myna run --input ic.yaml"
            + " && rm -rf myna_output myna_resources ic.yaml",
            shell=True,
            check=True,
            capture_output=True,
        ).stdout.decode("utf-8")
    assert "All output files are valid" in output
