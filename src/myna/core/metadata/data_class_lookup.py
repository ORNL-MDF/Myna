#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define common names for accessing metadata classes"""


def return_data_class_name(data_name):
    """Return name of data class given the common string name

    Args:
        data_name: string

    Returns:
        data_class_name: string of data class from myna.metadata
    """

    data_class_lookup = {
        "spot_size": "SpotSize",
        "laser_power": "LaserPower",
        "material": "Material",
        "preheat": "Preheat",
        "scanpath": "Scanpath",
        "stl": "STL",
        "layer_thickness": "LayerThickness",
        "part_id_map": "PartIDMap",
        "print_order": "PrintOrder",
    }
    try:
        data_class_name = data_class_lookup[data_name]
    except KeyError as e:
        print(e)
        print("ERROR: Data name is not valid. Valid data names:")
        for key in data_class_lookup.keys():
            print(f"    - {key}")
        exit()
    return data_class_name
