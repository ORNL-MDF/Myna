#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Base class for Myna file"""

import os
from typing_extensions import Literal
import numpy as np
import polars as pl


class File:
    """Base class for Myna file definitions."""

    def __init__(self, file):
        """Initialize with file path

        Args:
           file: filepath string
        """
        self.file = file
        self.filetype = None
        self.variables = []

    def file_is_valid(self):
        """Check if file is valid based on class/subclass requirements"""

        # Check for correct file type
        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False

        # If correct file type, then do filetype specific checks

        # For CSV files, check that expected columns are present
        if self.filetype.lower() in ["csv", ".csv"]:
            df = pl.read_csv(self.file, n_rows=0)
            cols = [x.lower() for x in df.columns]
            expected_cols = [x.fstr for x in self.variables]
            expected_cols_types = [x.dtype for x in self.variables]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)

        # For other file types, no specific checks are implemented
        return True

    def columns_are_valid(self, cols, expected_cols, expected_cols_types):
        """Check if file columns are valid and print informative warning."""

        if not set(expected_cols).issubset(cols):
            print("\nWARNING: The required headers were not found.")
            print("The following headers were found:")
            print(", ".join(cols))
            print("The correct format is a .csv file with headers:")
            print(", ".join(expected_cols))
            print(", ".join([f"{x}" for x in expected_cols_types]), "\n")
            return False
        return True

    def get_values_for_sync(
        self, mode: Literal["spatial_2d", "spatial_3d", "temporal"]
    ) -> tuple[
        tuple[np.ndarray, np.ndarray] | tuple[np.ndarray],
        list[np.ndarray],
        list[str],
        list[str],
    ]:
        """Get values at XY location in format expected for a layer-wise image sync

        Possible Exceptions:
        - `ValueError` for incorrect mode
        - `KeyError` for no columns found for requested mode
        - `NotImplementedError` if not implemented for the filetype
        """

        # Set locator variables for registration based on the mode
        locator_variables = set()
        if mode == "spatial_2d":
            locator_variables.update(["x (m)", "y (m)"])
        elif mode == "spatial_3d":
            locator_variables.update(["x (m)", "y (m)", "z (m)"])
        elif mode == "temporal":
            locator_variables.update(["time (s)"])
        else:
            raise ValueError(
                "mode argument must be 'spatial_2d', 'spatial_3d' or 'temporal'"
            )

        # Parse values based on filetype

        # For CSV files extract all values
        if self.filetype.lower() in [".csv", "csv"]:
            # Load the file with lowercase column names
            df = pl.read_csv(self.file)
            df = df.rename(mapping={x: x.lower() for x in df.columns})

            # If data is 3D, reduce to 2D if needed
            if (mode == "spatial_2d") and ("z (m)" in df.columns):
                df = df.filter("z (m)" == df["z (m)"].max())

            # Get the locator tuple
            locator = tuple(
                df[x].to_numpy() for x in locator_variables if x in df.columns
            )
            if len(locator) != len(locator_variables):
                msg = f"Not all {mode} locator variables in {self.__class__.__name__}"
                raise KeyError(msg)

            # Get the other values
            values = [
                df[x.fstr].to_numpy()
                for x in self.variables
                if x.fstr not in locator_variables
            ]
            if len(values) == 0:
                msg = f"No {mode} variables specified for {self.__class__.__name__}"
                raise KeyError(msg)

            # Get value names and units
            value_names = [
                x.name for x in self.variables if x.fstr not in locator_variables
            ]
            value_units = [
                x.units for x in self.variables if x.fstr not in locator_variables
            ]

            return locator, values, value_names, value_units

        # If the filetype is not implemented, raise a NotImplementedError
        raise NotImplementedError


class Variable:
    """Base class for Myna variable definitions."""

    def __init__(self, name: str, units: str = None, dtype=None, description: str = ""):
        """Initialize with variable name and units

        Args:
            name: variable name string
            units: variable units string
            dtype: variable data type (e.g. np.float32, np.int64)
        """
        self.name = name
        self.units = units
        self.dtype = dtype
        self.description = description
        self.fstr = f"{name} ({units})" if units else name
