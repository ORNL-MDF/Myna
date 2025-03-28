#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tools for file system operations"""
import os
import shutil
from pathlib import Path
import contextlib


@contextlib.contextmanager
def working_directory(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def is_executable(executable):
    """Checks if executable is valid, either as absolute path or accessible through PATH"""
    full_path = shutil.which(executable, mode=os.X_OK)
    if full_path is not None:
        return True
    else:
        return False
