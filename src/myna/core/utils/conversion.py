#
# Copyright (c) Oak Ridge National Laboratory.
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
    if isinstance(str_list, str):
        output = str_list.replace("[", "").replace("]", "").replace(" ", "").split(",")
    return output


def get_quoted_str(str_value):
    """Ensures that the string is contained in either single-quotes or double-quotes

    Args:
        str_value: string
    """
    fixed_str = str(str_value)

    for q in ["'", '"']:
        # Check for bracing quotes
        is_quoted = (str_value[0] == q) and (str_value[-1] == q)

        # Check for dangling quotes
        if (not is_quoted) and (str_value.count(q) % 2 == 1):
            if str_value[0] == q:
                fixed_str = str_value[1:]
            elif str_value[-1] == q:
                fixed_str = str_value[:-1]

        if is_quoted:
            # if string contains no single- or double-quotes
            if len(fixed_str.split(q)) == 1:
                return fixed_str
            # if string contains single-quotes
            if q == "'":
                return f'"{fixed_str}"'
            # if string contains double-quotes
            return f"'{fixed_str}'"

    return f'"{fixed_str}"'
