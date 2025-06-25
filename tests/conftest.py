#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--apps",
        action="store_true",
        default=False,
        help="Run tests which include simulation applications",
    )
    parser.addoption(
        "--serial",
        action="store_true",
        default=False,
        help="Run tests which include running serial examples",
    )
    parser.addoption(
        "--parallel",
        action="store_true",
        default=False,
        help="Run tests which include running parallel examples",
    )


def pytest_configure(config):
    """Configure the marker INI-file marker values"""
    config.addinivalue_line(
        "markers", "apps: mark application test (needs external dependency)"
    )
    config.addinivalue_line(
        "markers", "serial: mark serial example test (needs external dependency)"
    )
    config.addinivalue_line(
        "markers", "parallel: mark parallel example test (needs external dependency)"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--apps"):
        return
    if config.getoption("--serial"):
        return
    if config.getoption("--parallel"):
        return
    skip = {
        "apps": pytest.mark.skip(reason="Option --apps needed to run"),
        "serial": pytest.mark.skip(reason="Option --serial needed to run"),
        "parallel": pytest.mark.skip(reason="Option --parallel needed to run"),
    }
    for key, markskip in skip.items():
        for item in items:
            if key in item.keywords:
                item.add_marker(markskip)
