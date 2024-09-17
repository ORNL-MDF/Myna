#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define grain statistics data
"""
import pandas as pd
import os
from .file import *


class FileGrainSlice(File):
    """File format class for voxelized grain ids output in VTK format"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid.

        Checks if the file extension matches the ".csv" filetype.

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            return True

    def get_names_for_sync(self, prefix="myna"):
        """Return the names and units of fields available for syncing
        Args:
            prefix: prefix for output file name in synced file(s)

        Returns:
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list"""
        value_names = [
            f"{prefix}_meanGrainArea",
            f"{prefix}_nucleationFrac",
            f"{prefix}_wasserstein100Z",
        ]
        value_units = ["m^2", "", ""]
        return value_names, value_units

    def get_values_for_sync(self, prefix="myna"):
        """Get values in format expected from sync

        Args:
            prefix: prefix for output file name in synced file(s)

        Returns:
            x: numpy array of x-coordinates
            y: numpy array of y-coordinates
            values: list of numpy arrays of values for each (x,y) point
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list
        """

        # Read and extract values from the CSV file
        df = pd.read_csv(self.file)
        x = df["X (m)"]
        y = df["Y (m)"]
        value_names, value_units = self.get_names_for_sync(prefix=prefix)
        values = [
            df["Mean Grain Area (m^2)"].to_numpy(),
            df["Nulceated Fraction"].to_numpy(),
            df["Wasserstein distance (100-Z)"].to_numpy(),
        ]
        return x, y, values, value_names, value_units
