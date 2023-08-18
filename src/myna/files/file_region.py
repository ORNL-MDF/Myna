'''File format class for CSV file with region of interest location data'''
import pandas as pd
import os
from .file import *

class FileRegion(File):
    def __init__(self, file):
        File.__init__(self, file)      

    def file_is_valid(self):
        if os.path.splitext(self.file) != ".csv":
            print("ERROR: File for requirement FileRegion is not"
                    + " in the correct file format (.csv).")
            return False
        else:
            df = pd.read_csv(self.file)
            cols = [x.lower() for x in df.columns]
            expected_cols = ["id","x (m)","y (m)","layer_starts","layer_ends","part"]
            expected_cols_types = [int, float, float, int, int, str]
            if not set(expected_cols).issubset(cols):
                print("ERROR: The required headers were not found.")
                print("The correct format is a .csv file with headers:")
                print(", ".join(expected_cols))
                print(", ".join(expected_cols_types))
                return False
            return True
