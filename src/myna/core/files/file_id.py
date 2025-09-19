#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class for cluster id data"""

import pandas as pd
import os
from .file import *


class FileID(File):
    """Define file format class for a field of integer IDs.

    Intended for use with the `myna.components.cluster` classes.
    """

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "x (m)": float
        - "y (m)": float
        - "id": int

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            df = pd.read_csv(self.file, nrows=0)
            cols = [x.lower() for x in df.columns]
            expected_cols = ["x (m)", "y (m)", "id"]
            expected_cols_types = [float, float, int]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_values_for_sync(self, mode="spatial"):
        """Get values in format expected for sync

        Args:
            mode: "spatial" or "transient", determines the format of the output

        Returns:
            locator: (x,y) numpy arrays of coordinates if mode is "spatial", or
                     times numpy array if mode is "transient"
            values: list of numpy arrays of values for each (x,y) point
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list
        """

        # Load the file
        df = pd.read_csv(self.file)
        df = df.rename(str.lower, axis="columns")

        # Check if data is three-dimensional
        if "z (m)" in df.columns:
            df = df[df["z (m)"] == df["z (m)"].max()]

        # Set up location and value arrays to return
        x = df["x (m)"].to_numpy()
        y = df["y (m)"].to_numpy()
        locator = (x, y)
        value_names = ["id"]
        value_units = [""]
        values = [df["id"]]

        return locator, values, value_names, value_units
