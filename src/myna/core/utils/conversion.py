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
