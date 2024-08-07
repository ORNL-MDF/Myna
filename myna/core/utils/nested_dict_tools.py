#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tools for working with nested dictionaries"""


def nested_set(dict, keys, value):
    """Modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value


def nested_get(dict, keys):
    """Modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    return dict[keys[-1]]
