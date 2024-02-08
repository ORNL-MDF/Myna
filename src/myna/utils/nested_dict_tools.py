"""Tools for working with nested dictionaries"""


def nested_set(dict, keys, value):
    """modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value


def nested_get(dict, keys):
    """modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    return dict[keys[-1]]
