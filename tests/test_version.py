#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
from importlib.metadata import version

import myna


# This test is primarily intended to ensure the test suite itself is working.
def test_version():
    assert version("myna") == "1.1.0.dev0"
