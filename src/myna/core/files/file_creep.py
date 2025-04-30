#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for creep data"""

import os
import polars as pl
from .file import File


class FileCreepTimeSeries(File):
    """File format class for creep time series data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid.

        Checks if the file extension matches the ".csv" filetype.
        Requires the columns below, additional columns are ignored:
        - "time (s)": (float) the elapsed time in the simulation
        - "strain": (float) the average engineering strain of the simulated volume

        Returns:
           Boolean
        """

        # Check for correct file type
        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False

        # If correct file type, then check that expected columns are present
        df = pl.read_csv(self.file, n_rows=0)
        cols = [x.lower() for x in df.columns]
        expected_cols = ["time (s)", "strain"]
        expected_cols_types = [float, float]
        return self.columns_are_valid(cols, expected_cols, expected_cols_types)

    def get_names_for_sync(self, prefix):
        """Return the names and units of fields available for syncing"""
        raise NotImplementedError

    def get_values_for_sync(self, prefix):
        """Get values in format expected for sync"""
        raise NotImplementedError
