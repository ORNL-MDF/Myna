"""File format class for CSV file with region of interest location data"""

import pandas as pd
import os
from .file import *


class FileRegion(File):
    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"

    def file_is_valid(self):
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
