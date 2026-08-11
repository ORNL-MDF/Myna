#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Version parsing and comparison helpers."""

import re


def parse_version_tuple(version):
    """Convert a dotted numeric version string into a comparable tuple."""
    match = re.search(r"\d+(?:\.\d+)+", version)
    if match is None:
        raise ValueError(f"Could not compare unrecognized version {version!r}.")
    return tuple(int(value) for value in match.group(0).split("."))


def version_at_least(version, minimum_version):
    """Return whether ``version`` meets the requested minimum version."""
    return parse_version_tuple(version) >= parse_version_tuple(minimum_version)
