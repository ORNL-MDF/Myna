"""File format class for cluster id data"""

import pandas as pd
import os
from .file import *


class FileID(File):
    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
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

    def get_values_for_sync(self, prefix="myna"):
        """Get values in format expected for sync"""
        # Load the file
        df = pd.read_csv(self.file)
        df = df.rename(str.lower, axis="columns")

        # Check if data is three-dimensional
        if "z (m)" in df.columns:
            df = df[df["z (m)"] == df["z (m)"].max()]

        # Set up location and value arrays to return
        x = df["x (m)"].to_numpy()
        y = df["y (m)"].to_numpy()
        value_names = [f"id"]
        value_units = [""]
        values = [df["id"]]
        return x, y, values, value_names, value_units
