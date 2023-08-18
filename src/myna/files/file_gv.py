'''File format class for temperature gradient (G) and solidification 
velocity (V) data'''
import pandas as pd
import os
from .file import *

class FileGV(File):
    def __init__(self, file):
        File.__init__(self, file)
    
    def file_is_valid(self):
        if os.path.splitext(self.file)[-1] != ".csv":
            print(f"ERROR: File {self.file} for requirement FileGV is not"
                    + " in the correct file format (.csv).")
            return False
            
        else:
            df = pd.read_csv(self.file, nrows=0)
            cols = [x.lower() for x in df.columns]
            expected_cols = ["x (m)","y (m)","g","v"]
            expected_cols_types = [int, float, float, int, int, str]
            if not set(expected_cols).issubset(cols):
                print(f"ERROR: The required headers were not found in {self.file}.")
                print("Found headers:")
                print(", ".join(cols))
                print("The correct format is a .csv file with headers:")
                print(", ".join(expected_cols))
                print(", ".join(expected_cols_types))
                return False
            return True
