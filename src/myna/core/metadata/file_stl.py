#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading behavior for STL geometry files in databases"""

from .file import *
import os


class STL(PartFile):
    """File containing the STL for a part in a build.

    Implemented datatypes:
    - PeregrineDB"""

    def __init__(self, datatype, part):
        PartFile.__init__(self, datatype, part)
        self.file_database = datatype.load(type(self), part=self.part)
        self.file_local = os.path.join(self.resource_dir, "part.stl")
