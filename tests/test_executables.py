#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
import subprocess


@pytest.mark.apps
def test_exaca():
    """This test checks if ExaCA is in the current environment, which is the
    preferred method for accessing the executable in the ExaCA applications"""
    # This assumes it is on the path
    output = subprocess.run(
        'ExaCA | grep "ExaCA version"', shell=True, check=False, capture_output=True
    ).stdout.decode("utf-8")
    assert "ExaCA version" in output


@pytest.mark.apps
def test_openfoam_10():
    """This test checks if OpenFOAM-10 is activated in the current environment,
    which is required for the AdditiveFOAM apps"""
    output = subprocess.run(
        'checkMesh -help | grep "Using:"', shell=True, check=False, capture_output=True
    ).stdout.decode("utf-8")
    assert "OpenFOAM-10" in output


@pytest.mark.apps
def test_additivefoam():
    """This test checks if `additiveFoam` is on the current path"""
    output = subprocess.run(
        'additiveFoam | grep "AdditiveFOAM Information"',
        shell=True,
        check=False,
        capture_output=True,
    ).stdout.decode("utf-8")
    assert "AdditiveFOAM" in output


@pytest.mark.apps
def test_thesis():
    """This test checks if `3DThesis` is on the current path"""
    output = subprocess.run(
        '3DThesis | grep "3DThesis"', shell=True, check=False, capture_output=True
    ).stderr.decode("utf-8")
    assert "3DThesis" in output
