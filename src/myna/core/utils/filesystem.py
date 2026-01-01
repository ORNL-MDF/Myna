#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tools for file system operations"""

import os
import json
import yaml
import shutil
from typing import Any
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


def strf_datetime(datetime_obj):
    """Return the current date and time as a pretty string"""
    return datetime_obj.strftime("%Y-%m-%d %H:%M:%S")


def load_json_yaml_file(filepath: str | Path, enforce_type=None) -> Any:
    """Loads a dictionary from a JSON or YAML file, optionally enforcing a top-level
    datatype (e.g., dict or list)"""
    with open(filepath, "r") as f:
        suffix = Path(filepath).suffix
        contents = {}
        if suffix in [".yml", ".yaml"]:
            contents = yaml.safe_load(f)
        elif suffix in [".json"]:
            contents = json.load(f)
        if enforce_type is not None:
            if not isinstance(contents, enforce_type):
                raise ValueError(
                    f"Top-level contents of {filepath} are"
                    f"{type(contents)} but are expected to be {enforce_type}"
                )
        return contents
