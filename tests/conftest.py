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
        "--interfaces",
        action="store_true",
        default=False,
        help="Run tests which include simulation interfaces",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "interfaces: mark interface test (needs external dependency)"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--interfaces"):
        return
    skip = pytest.mark.skip(reason="Option --interfaces needed to run")
    for item in items:
        if "interfaces" in item.keywords:
            item.add_marker(skip)
