""" Define the file format class for reduced solidification data."""

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

    def get_values_for_sync(self, prefix="myna"):
        """Get values in format expected for sync

        Args:
            prefix: prefix for output file name in synced file(s)

        Returns:
            x: numpy array of x-coordinates
            y: numpy array of y-coordinates
            values: list of numpy arrays of values for each (x,y) point
            value_names: list of string names for each field in the values list
            value_units: list of string units for each field in the values list
        """

        # Load the file
        df = pd.read_csv(self.file)
        df = df.rename(str.lower, axis="columns")

        # Return top-surface values only
        df = df[df["z"] == df["z"].max()]

        # Set up location and value arrays to return
        x = df["x"].to_numpy()
        y = df["y"].to_numpy()
        value_names = [
            f"{prefix}_t_melt",
            f"{prefix}_t_solidify",
            f"{prefix}_cooling_rate",
        ]
        value_units = ["s", "s", "K/s"]
        values = [
            df["tm"].to_numpy(),
            df["ts"].to_numpy(),
            df["cr"].to_numpy(),
        ]
        return x, y, values, value_names, value_units
