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
        "--examples",
        action="store_true",
        default=False,
        help="Run tests which include running examples",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "apps: mark application test (needs external dependency)"
    )
    config.addinivalue_line(
        "markers", "examples: mark example test (needs external dependency)"
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--apps"):
        return
    if config.getoption("--examples"):
        return
    skip = {
        "apps": pytest.mark.skip(reason="Option --apps needed to run"),
        "examples": pytest.mark.skip(reason="Option --examples needed to run"),
    }
    for key, markskip in skip.items():
        for item in items:
            if key in item.keywords:
                item.add_marker(markskip)
