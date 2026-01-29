#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tools for parsing lists of layer numbers"""

import numpy as np


def get_adjacent_layer_regions(myna_data, region_size=20):
    """
    Args:
      myna_data: data dictionary from a configured Myna input file
      region_size: maximum number of adjacent layers to include in a region

    Returns:
      part_layer_sets: dictionary with strings of part names as the keys. Each entry
                       contains a list of dictionaries where each dictionary represents
                       a set of adjacent layers with keys "layer_start" (int),
                       "layer_end" (int), "layers" (list of int)
    """

    # Iterate through files and create part-layer dictionary
    part_layer_dict = {}
    for part_name in myna_data["build"]["parts"].keys():
        part_dict = myna_data["build"]["parts"].get(part_name)
        layers = part_dict.get("layers")
        part_layer_dict[part_name] = layers

    # Sort layers
    for part in part_layer_dict.keys():
        part_layer_dict[part] = sorted(part_layer_dict[part])

    # Determine if part & layer are adjacent to last layer
    # and if not, then write region info to lists
    part_layer_sets = {}
    previous_layer = -1
    for part in part_layer_dict.keys():
        part_layers = part_layer_dict[part]
        part_layer_sets[part] = []

        for i, layer in enumerate(part_layers):
            # Determine if layer is adjacent to the last layer
            if i == 0:
                layer_start = layer
                layer_end = layer
            elif layer == previous_layer + 1:
                layer_end = layer

            # Determine if a region needs to be defined
            is_last_layer_in_region = (layer_end - layer_start) == region_size
            is_last_layer = layer == np.max(part_layers)
            if is_last_layer_in_region or is_last_layer:
                part_layer_sets[part].append(
                    {
                        "layer_start": layer_start,
                        "layer_end": layer_end,
                        "layers": list(np.arange(layer_start, layer_end + 1)),
                    }
                )

            # Set last layer
            previous_layer = layer

    return part_layer_sets
