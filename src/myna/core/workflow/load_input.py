#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import yaml


def load_input(filename):
    """Load input file into dictionary

    Args:
        filename: path to input file (str) to load

    Returns:
        settings: dictionary of input file settings
    """

    input_file = filename
    with open(input_file, "r") as f:
        file_type = input_file.split(".")[-1]
        if (file_type.lower() == "yaml") or (file_type.lower() == "myna-workspace"):
            settings = yaml.safe_load(f)
        else:
            print(
                f'ERROR: Unsupported input file type "{file_type}". Must be .yaml format'
            )

        # Enforce that main keys exist
        for key in ["steps", "data", "myna"]:
            if settings.get(key) is None:
                settings[key] = {}

    return settings
