#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import subprocess


def foam_dict_get(entry, filepath):
    """Gets a value from a foamDictionary file."""
    command = ["foamDictionary", "-entry", entry, "-value", filepath]
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()


def foam_dict_set(entry, value, filepath):
    """Gets a value from a foamDictionary file."""
    command = "foamDictionary", "-entry", entry, "-set", str(value), filepath
    subprocess.run(command, check=True)
