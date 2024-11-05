#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for region of interest location data"""

import pandas as pd
import os
from .file import *


class FileRegion(File):
    """File format class for CSV file with region of interest location data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "id": int
        - "x": float
        - "y": float
        - "layer_starts": int
        - "layer_ends": int
        - "part": str

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            df = pd.read_csv(self.file)
            cols = [x.lower() for x in df.columns]
            expected_cols = [
                "id",
                "x (m)",
                "y (m)",
                "layer_starts",
                "layer_ends",
                "part",
            ]
            expected_cols_types = [int, float, float, int, int, str]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)


class FileBuildRegion(File):
    """File format class for CSV file with a rectangular region of interest location
    data in a build that can span multiple parts"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "id": int
        - "x_min (m)": float
        - "y_min (m)": float
        - "x_max (m)": float
        - "y_max (m)": float
        - "layer_starts": int
        - "layer_ends": int
        - "parts": str ("all" or part name separated by underscores, e.g., "P1_P2")

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            df = pd.read_csv(self.file)
            cols = [x.lower() for x in df.columns]
            expected_cols = [
                "id",
                "x_min (m)",
                "y_min (m)",
                "x_max (m)",
                "y_max (m)",
                "layer_starts",
                "layer_ends",
            ]
            expected_cols_types = [int, float, float, float, float, int, int, str]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)
