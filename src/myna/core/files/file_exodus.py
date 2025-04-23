#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for Exodus mesh output data"""

import os
from .file import *


class FileExodus(File):
    """File format class for Exodus mesh data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".e"

    def file_is_valid(self):
        """Determines if the associated file is valid.

        Checks if the file extension matches the ".e" filetype.

        Returns:
           Boolean
        """

        if (self.filetype is not None) and (
            os.path.splitext(self.file)[-1] != self.filetype
        ):
            return False
        else:
            return True
