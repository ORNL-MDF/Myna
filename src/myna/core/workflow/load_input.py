#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import json
import yaml


def validate_required_input_keys(settings):
    """Validates the settings dictionary to ensure it has the necessary keys for
    a Myna input dictionary

    Args:
        settings: (dict) input settings

    Returns:
        (dict) validated input settings
    """
    # Enforce that main keys exist
    for key in ["steps", "data", "myna"]:
        if settings.get(key) is None:
            settings[key] = {}

    return settings


def load_input(filename):
    """Load input file into dictionary

    Args:
        filename: path to input file (str) to load

    Returns:
        settings: dictionary of input file settings
    """

    with open(filename, "r", encoding="utf-8") as f:
        file_type = os.path.splitext(filename)[1].lower()
        if (file_type == ".yaml") or (file_type == ".myna-workspace"):
            settings = yaml.safe_load(f)
        elif (file_type == ".json") or (file_type == "myna-workspace-json"):
            settings = json.load(f)
        else:
            error_msg = (
                f'Unsupported input file type "{file_type}".'
                ' Accepted input file formats are ".yaml" and ".json".'
            )
            raise ValueError(error_msg)

    return validate_required_input_keys(settings)


def write_input(settings, filename):
    """Write Myna input dictionary to file

    Args:
        settings: (dict) Myna input dictionary
        filename: (str) path to file to write
    """

    # Ensure that required input keys exist
    settings = validate_required_input_keys(settings)

    # Write the Myna input dictionary to a file
    with open(filename, "w", encoding="utf-8") as f:
        file_type = os.path.splitext(filename)[1].lower()
        if (file_type == ".yaml") or (file_type == ".myna-workspace"):
            yaml.safe_dump(
                settings, f, sort_keys=False, default_flow_style=None, indent=2
            )
        elif (file_type == ".json") or (file_type == "myna-workspace-json"):
            json.dump(settings, f, sort_keys=False, indent=2)
        else:
            error_msg = (
                f'Unsupported input file type "{file_type}".'
                ' Accepted input file formats are ".yaml" and ".json".'
            )
            raise ValueError(error_msg)
