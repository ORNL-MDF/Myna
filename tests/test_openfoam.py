import pytest
import subprocess

# This test checks if OpenFOAM-10 is activated in the current environment,
# which is required for the AdditiveFOAM interfaces
@pytest.mark.interfaces
def test_openfoam_10():
    output = subprocess.check_output("checkMesh -help | grep Using:", shell=True).decode("utf-8")
    assert "OpenFOAM-10" in output
