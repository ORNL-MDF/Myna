#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest

from myna.core.utils import parse_version_tuple, version_at_least


@pytest.mark.parametrize(
    ("version", "expected"),
    [
        ("4.0.0", (4, 0, 0)),
        ("3DThesis 4.1.2", (4, 1, 2)),
        ("ExaCA version: 2.1.0-dev", (2, 1, 0)),
    ],
)
def test_parse_version_tuple_extracts_numeric_components(version, expected):
    assert parse_version_tuple(version) == expected


def test_parse_version_tuple_rejects_unrecognized_versions():
    with pytest.raises(ValueError, match="Could not compare unrecognized version"):
        parse_version_tuple("development build")


@pytest.mark.parametrize(
    ("version", "minimum_version", "expected"),
    [
        ("4.0.0", "4.0.0", True),
        ("4.0.1", "4.0.0", True),
        ("3.9.9", "4.0.0", False),
    ],
)
def test_version_at_least(version, minimum_version, expected):
    assert version_at_least(version, minimum_version) is expected
