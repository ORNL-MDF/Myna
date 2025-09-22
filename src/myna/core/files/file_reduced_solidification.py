#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the file format class for reduced solidification data."""

import pandas as pd
import os
from .file import *


class FileReducedSolidification(File):
    """File format class for reduced solidification data.

    Based on a the reduced data format defined in:

    M. Rolchigo, B. Stump, J. Belak, and A. Plotkowski, "Sparse thermal data
    for cellular automata modeling of grain structure in additive
    manufacturing," Modelling Simul. Mater. Sci. Eng. 28, 065003.
    https://doi.org/10.1088/1361-651X/ab9734
    """

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "x": float
        - "y": float
        - "z": float
        - "tm": float
        - "ts": float
        - "cr": float

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
            expected_cols = ["x", "y", "z", "tm", "ts", "cr"]
            expected_cols_types = [float, float, float, float, float]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_values_for_sync(self, mode="spatial"):
        """Get values in format expected for sync

        Args:
            mode: mode for syncing (only "spatial" is implemented)

        Returns:
            locator: (x,y) numpy arrays of coordinates if mode is "spatial", or
                     times numpy array if mode is "temporal"
            values: list of numpy arrays of values for each (x,y) point
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list
        """
        if mode == "temporal":
            msg = f"Transient sync not implemented for {self.__class__.__name__}"
            raise NotImplementedError(msg)

        # Load the file
        df = pd.read_csv(self.file)
        df = df.rename(str.lower, axis="columns")

        # Return top-surface values only
        df = df[df["z"] == df["z"].max()]

        # Set up location and value arrays to return
        x = df["x"].to_numpy()
        y = df["y"].to_numpy()
        locator = (x, y)
        value_names = [
            "t_melt",
            "t_solidify",
            "cooling_rate",
        ]
        value_units = ["s", "s", "K/s"]
        values = [
            df["tm"].to_numpy(),
            df["ts"].to_numpy(),
            df["cr"].to_numpy(),
        ]
        return locator, values, value_names, value_units
