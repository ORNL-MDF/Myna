#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Shared test paths for example fixtures and runnable cases."""

from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
EXAMPLES_DIR = REPO_ROOT / "examples"
CASES_DIR = EXAMPLES_DIR / "cases"
DATABASES_DIR = EXAMPLES_DIR / "databases"
SHARED_DIR = EXAMPLES_DIR / "shared"
