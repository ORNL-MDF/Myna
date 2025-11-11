#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading behavior for build-layer part ID maps"""

from .file import *
import os


class PartIDMap(BuildLayerPartsetFile):
    """File containing an array of XY locations and part IDs for a build layer

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, partset, layer):
        BuildLayerPartsetFile.__init__(self, datatype, partset, layer)
        self.file_database = datatype.load(type(self), part=partset, layer=self.layer)
        self.file_local = os.path.join(self.resource_dir, f"part_ids_{layer}.parquet")
