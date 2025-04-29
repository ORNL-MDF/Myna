#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Conversion functions"""


def str_to_list(str_list):
    """Converts string containing list to Python list"""
    output = None
    if type(str_list) == str:
        output = str_list.replace("[", "").replace("]", "").replace(" ", "").split(",")
    return output


def get_quoted_str(str_value):
    """Ensures that the string is contained in either single-quotes or double-quotes

    Args:
        str_value: string
    """
    assert isinstance(str_value, str)
    for q in ["'", '"']:
        if (str_value[0] == q) and (str_value[-1] == q):
            # if string contains no single- or double-quotes
            if len(str_value.split(q)) == 1:
                return str_value
            # if string contains single-quotes
            if q == "'":
                return f'"{str_value}"'
            # if string contains double-quotes
            return f"'{str_value}'"
    return f'"{str_value}"'
