#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class related to the temperature gradient (G) and
solidification velocity (V)
"""

import polars as pl
import os
from .file import *


class FileGV(File):
    """File format class for temperature gradient (G) and solidification
    velocity (V) data
    """

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "x (m)": float
        - "y (m)": float
        - "g (k/m)": float
        - "v (m/s)": float

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            df = pl.read_csv(self.file, n_rows=0)
            cols = [x.lower() for x in df.columns]
            expected_cols = ["x (m)", "y (m)", "g (k/m)", "v (m/s)"]
            expected_cols_types = [float, float, float, float]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_names_for_sync(self, mode="spatial"):
        """Return the names and units of fields available for syncing
        Args:
            mode: mode for syncing (only "spatial" is implemented)

        Returns:
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list"""
        if mode == "transient":
            msg = f"Transient sync not implemented for {self.__class__.__name__}"
            raise NotImplementedError(msg)
        value_names = ["G", "R", "cooling_rate"]
        value_units = ["K/m", "m/s", "K/s"]
        return value_names, value_units

    def get_values_for_sync(self, mode="spatial"):
        """Get values in format expected for sync

        Args:
            mode: mode for syncing (only "spatial" is implemented)

        Returns:
            locator: (x,y) numpy arrays of coordinates if mode is "spatial", or
                     times numpy array if mode is "transient"
            values: list of numpy arrays of values for each (x,y) point
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list
        """
        if mode == "transient":
            msg = f"Transient sync not implemented for {self.__class__.__name__}"
            raise NotImplementedError(msg)

        # Load the file
        df = pl.read_csv(self.file)
        df = df.with_columns(pl.all().name.to_lowercase())

        # Check if data is three-dimensional
        if "z (m)" in df.columns:
            df = df.filter(pl.col("z (m)") == df["z (m)"].max())

        # Calculate derived field(s)
        df = df.with_columns((pl.col("g (k/m)") * pl.col("v (m/s)")).alias("cr (k/s)"))

        # Set up location and value arrays to return
        x = df["x (m)"].to_numpy()
        y = df["y (m)"].to_numpy()
        locator = (x, y)
        value_names, value_units = self.get_names_for_sync(mode="spatial")
        values = [
            df["g (k/m)"].to_numpy(),
            df["v (m/s)"].to_numpy(),
            df["cr (k/s)"].to_numpy(),
        ]
        return locator, values, value_names, value_units
