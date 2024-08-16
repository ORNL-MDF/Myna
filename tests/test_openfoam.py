#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
import subprocess


# This test checks if OpenFOAM-10 is activated in the current environment,
# which is required for the AdditiveFOAM apps
@pytest.mark.apps
def test_openfoam_10():
    output = subprocess.check_output(
        "checkMesh -help | grep Using:", shell=True
    ).decode("utf-8")
    assert "OpenFOAM-10" in output
