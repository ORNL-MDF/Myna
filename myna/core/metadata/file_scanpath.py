#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading behavior for scan path files in databases"""

from .file import *
import os


class Scanpath(LayerFile):
    """File containing the scan path for a layer of a part in a build.

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, part, layer):
        LayerFile.__init__(self, datatype, part, layer)
        self.file_database = datatype.load(type(self), part=self.part, layer=self.layer)
        self.file_local = os.path.join(self.resource_dir, "scanpath.txt")
