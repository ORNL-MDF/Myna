#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class related to the spatial distribution of melt pool geometries"""

import os
import pandas as pd
import numpy as np
from .file import File


class FileMeltPoolGeometry(File):
    """File format class for melt pool geometries"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "Time (s)": float
        - "x (m)": float
        - "y (m)": float
        - "Length (m)": float
        - "Width (m)": float
        - "Depth (m)": float


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
            expected_cols = [
                "time (s)",
                "x (m)",
                "y (m)",
                "length (m)",
                "width (m)",
                "depth (m)",
            ]
            expected_cols_types = [float, float, float, float, float, float]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_names_for_sync(self, mode="transient"):
        """Return the names and units of fields available for syncing
        Args:
            mode: mode for syncing ("transient" or "spatial")

        Returns:
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list"""
        if mode == "spatial":
            value_names = [
                "time",
                "length",
                "width",
                "depth",
            ]
            value_units = ["s", "m", "m", "m"]
            return value_names, value_units

        value_names = [
            "length",
            "width",
            "depth",
        ]
        value_units = ["m", "m", "m"]
        return value_names, value_units

    def get_values_for_sync(self, mode="transient"):
        """Get values in format expected for sync

        Args:
            mode: mode for syncing ("transient" or "spatial")

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

        if mode == "spatial":

            # Check if data is three-dimensional
            if "z (m)" in df.columns:
                df = df[df["z (m)"] == df["z (m)"].max()]
            df = df.dropna()

            # Set up location and value arrays to return
            x = df["x (m)"].to_numpy()
            y = df["y (m)"].to_numpy()
            locator = (x, y)
            value_names, value_units = self.get_names_for_sync(mode="spatial")
            values = [
                df["time (s)"].to_numpy(),
                df["length (m)"].to_numpy(),
                df["width (m)"].to_numpy(),
                df["depth (m)"].to_numpy(),
            ]
            return locator, values, value_names, value_units

        # Set up time series and value arrays to return
        value_names, value_units = self.get_names_for_sync(mode="transient")
        locator = df["time (s)"].to_numpy()
        values = [
            df["length (m)"].to_numpy(),
            df["width (m)"].to_numpy(),
            df["depth (m)"].to_numpy(),
        ]
        return locator, values, value_names, value_units
