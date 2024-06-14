"""Define file format class related to the spatial distribution of temperature (T)
"""

import pandas as pd
import os
from .file import *


class FileTemperature(File):
    """File format class for temperature (T)"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
        """Determines if the associated file is valid

        Requires the columns below, additional columns are ignored:
        - "x (m)": float
        - "y (m)": float
        - "t (k)": float

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
            expected_cols = ["x (m)", "y (m)", "t (k)"]
            expected_cols_types = [float, float, float]
            return self.columns_are_valid(cols, expected_cols, expected_cols_types)
