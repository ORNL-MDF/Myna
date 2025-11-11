#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for a directory with NIST AM-Bench 2022 build data"""

import os
import json
from myna.core.db import Database
from myna.core import metadata
from myna.core.utils import nested_get


class MynaJSON(Database):
    """Database stored in a JSON dictionary containing Myna data"""

    def __init__(self):
        Database.__init__(self)
        self.description = "Myna JSON database"
        self.build_segmentation_type = "layer"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the JSON-containing build data
        """
        self.path = path
        self.path_dir = os.path.dirname(self.path)

    def exists(self):
        return os.path.exists(self.path)

    def load(self, metadata_type, part=None, layer=None):
        """Load and return a metadata value from the database"""
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ==============================================================================
        # Data values
        # ==============================================================================
        if metadata_type == metadata.Material:
            return nested_get(data, ["material"])

        elif metadata_type == metadata.LayerThickness:
            return nested_get(data, ["layer_thickness"])  # mm

        elif metadata_type == metadata.Preheat:
            return nested_get(data, ["preheat"])  # K

        elif metadata_type == metadata.PartIDMap:
            return nested_get(data, ["print_order"])

        elif metadata_type == metadata.LaserPower:
            return nested_get(data, [part, "laser_power"])  # W

        elif metadata_type == metadata.SpotSize:
            return nested_get(data, [part, "spot_size"])  # mm, D4sigma

        # ==============================================================================
        # File paths
        # ==============================================================================
        elif metadata_type == metadata.Scanpath:
            return self.get_scan_path(data, part, layer)

        elif metadata_type == metadata.STL:
            return nested_get(data, ["stl"])

        elif metadata_type == metadata.PartIDMap:
            return nested_get(data, ["part_id_map"])

    def layer_str(self, layernumber):
        """Return formatted layer number string"""
        return f"{int(layernumber):07}"

    def get_scan_path(self, data, part, layer):
        """Returns the scanpath file path, converting or extracting information to a
        file if necessary"""
        pathtype = nested_get(data, [part, layer, "scanpath", "type"])
        if pathtype == "mynafile":
            return nested_get(data, [part, layer, "scanpath", "file"])
        else:
            raise KeyError(
                f'Invalid entry for "{part}/{layer}/scanpath/type": "{pathtype}"'
            )
