#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for Exodus mesh output data"""

from .file import *


class FileExodus(File):
    """File format class for Exodus mesh data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".e"
