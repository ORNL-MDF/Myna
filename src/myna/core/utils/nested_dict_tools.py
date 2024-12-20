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


def nested_get(dict, keys, default_value=None):
    """Gets the value of a nested dictionary given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict.setdefault(keys[-1], default_value)
    return dict[keys[-1]]


def nested_find_all(dictionary, target_key):
    """Gets the values of all matching keys in the nested dictionary at any level

    Args:
        dictionary: dictionary to parse
        key: key to match
    """
    matches = []
    if target_key in dictionary:
        matches.append(dictionary[target_key])
    for key, value in dictionary.items():
        if isinstance(value, dict):
            nested_matches = nested_find_all(dictionary[key], target_key)
            matches.extend(nested_matches)
    return matches


def get_synonymous_key(dict_obj, synonym_list):
    """Returns the object at the first matching key from a dictionary-like object
    given a list of synonymous keys

    Args:
        dict_obj: dictionary-like object, e.g., dict or h5py.File()
        synonym_list: list of synonymous keys to check

    Returns:
        entry_name: first matching key
    """
    matches = [syn in dict_obj for syn in synonym_list]
    entry_name = synonym_list[matches.index(True)]
    return entry_name
