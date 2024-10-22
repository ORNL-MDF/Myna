#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for VTK output data"""

import pandas as pd
import os
from .file import *


class FileVTK(File):
    """File format class for VTK output data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".vtk"

    def file_is_valid(self):
        """Determines if the associated file is valid.

        Checks if the file extension matches the ".vtk" filetype.

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            return True
