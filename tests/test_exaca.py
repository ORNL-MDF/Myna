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


# This test checks if ExaCA is in the current environment,
# which is the preferred method for accessing the executable in the ExaCA applications
@pytest.mark.apps
def test_exaca():
    # This assumes it is on the path
    output = subprocess.run("ExaCA", shell=True, capture_output=True)
    # Ignore that this fails for now - just make sure the exe is available
    # First output is always version info
    assert "ExaCA version" in str(output.stdout.splitlines()[0])
