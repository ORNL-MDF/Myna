#
# Copyright (c) Oak Ridge National Laboratory.
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


def get_validated_input_filetype(filename):
    """Returns the validate input filetype ("yaml" or "json") and throws an error
    if the input type is not valid.

    Args:
        filename: (str) the name or path of the input file"""
    filetype = os.path.splitext(filename)[1].lower()
    if is_yaml_type(filetype):
        return "yaml"
    elif is_json_type(filetype):
        return "json"
    else:
        error_msg = (
            f'Unsupported input file type "{filetype}".'
            " Accepted input file formats are:"
            '\n- ".yaml" or ".myna-workspace"'
            '\n- ".json" or ".myna-workspace-json"'
        )
        raise ValueError(error_msg)


def is_yaml_type(filetype):
    """Boolean of if file_type if Myna-accepted YAML format"""
    return filetype in (".yaml", ".myna-workspace")


def is_json_type(filetype):
    """Boolean of if file_type if Myna-accepted JSON format"""
    return filetype in (".json", ".myna-workspace-json")


def load_input(filename):
    """Load input file into dictionary

    Args:
        filename: path to input file (str) to load

    Returns:
        settings: dictionary of input file settings
    """

    with open(filename, "r", encoding="utf-8") as f:
        filetype = get_validated_input_filetype(filename)
        if filetype == "yaml":
            settings = yaml.safe_load(f)
        else:
            settings = json.load(f)
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
        filetype = get_validated_input_filetype(filename)
        if filetype == "yaml":
            yaml.safe_dump(
                settings, f, sort_keys=False, default_flow_style=None, indent=2
            )
        else:
            json.dump(settings, f, sort_keys=False, indent=2)
