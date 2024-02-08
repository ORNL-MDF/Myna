"""File format class for temperature gradient (G) and solidification 
velocity (V) data"""
import pandas as pd
import os
from .file import *


class FileGV(File):
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
            expected_cols = ["x (m)", "y (m)", "g (k/m)", "v (m/s)"]
            expected_cols_types = [float, float, float, float]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_values_for_sync(self, prefix="myna"):
        """Get values in format expected for sync"""
        # Load the file
        df = pd.read_csv(self.file)
        df = df.rename(str.lower, axis="columns")

        # Check if data is three-dimensional
        if "z (m)" in df.columns:
            df = df[df["z (m)"] == df["z (m)"].max()]

        # Calculate derived field(s)
        df["cr (k/s)"] = df["g (k/m)"] * df["v (m/s)"]

        # Set up location and value arrays to return
        x = df["x (m)"].to_numpy()
        y = df["y (m)"].to_numpy()
        value_names = [f"{prefix}_G", f"{prefix}_R", f"{prefix}_cooling_rate"]
        value_units = ["K/m", "m/s", "K/s"]
        values = [
            df["g (k/m)"].to_numpy(),
            df["v (m/s)"].to_numpy(),
            df["cr (k/s)"].to_numpy(),
        ]
        return x, y, values, value_names, value_units
