#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#


def pytest_configure(config):
    """Configure the marker INI-file marker values"""
    config.addinivalue_line(
        "markers", "apps: mark tests with external application dependency"
    )
    config.addinivalue_line(
        "markers", "examples: mark tests that run cases in the `examples` directory"
    )
    config.addinivalue_line(
        "markers", "parallel: mark tests that require multiple cores to run"
    )
