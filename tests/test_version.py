#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from importlib.metadata import version
import os


# This test is primarily intended to ensure the test suite itself is working.
def test_version():
    path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(path, "..", "pyproject.toml")) as f:
        lines = f.readlines()

    toml_version = (
        lines[["version = " in l for l in lines].index(True)]
        .split(" = ")[-1]
        .split('"')[1]
    )
    assert version("myna") == toml_version
