#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for VTK output data"""

from .file import File


class FileVTK(File):
    """File format class for VTK output data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".vtk"
