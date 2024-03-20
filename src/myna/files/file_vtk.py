"""File format class for VTK output data"""

import pandas as pd
import os
from .file import *


class FileVTK(File):
    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".vtk"

    def file_is_valid(self):
        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            return True
