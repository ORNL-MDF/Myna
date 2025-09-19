#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Base class for Myna file"""
from typing_extensions import Literal
import numpy as np


class File:
    """Base class for Myna file definitions.

    Raises:
       file_is_valid: NotImplementedError in base class
       get_values_for_sync: NotImplementedError in base class
    """

    def __init__(self, file):
        """Initialize with file path

        Args:
           file: filepath string
        """
        self.file = file
        self.filetype = None

    def file_is_valid(self):
        """Check if file is valid based on class/subclass requirements"""
        raise NotImplementedError

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

    def get_names_for_sync(
        self, mode: Literal["spatial", "transient"]
    ) -> tuple[list[str], list[str]]:
        """Return the names and units of fields available for syncing"""
        raise NotImplementedError

    def get_values_for_sync(self, mode: Literal["spatial", "transient"]) -> tuple[
        tuple[np.ndarray, np.ndarray] | np.ndarray,
        list[np.ndarray],
        list[str],
        list[str],
    ]:
        """Get values at XY location in format expected for a layer-wise image sync"""
        raise NotImplementedError
