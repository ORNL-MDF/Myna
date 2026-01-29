#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define Component subclasses for clustering data

Available subclasses:
   ComponentCluster
   ComponentClusterSolidification
   ComponentClusterSupervoxel
"""

from .component import Component
from myna.core.files import FileGV, FileID


class ComponentCluster(Component):
    """Part-wise Component that outputs spatially-varying data labels in the
    `FileID` class format.
    """

    def __init__(self):
        Component.__init__(self)
        self.output_requirement = FileID
        self.types.append("part")


class ComponentClusterSolidification(ComponentCluster):
    """Layer-wise Component that outputs spatially-varying data in the
    FileID` class format and requires input from solidification
    data file of class `FileGV`.
    """

    def __init__(self):
        ComponentCluster.__init__(self)
        self.input_requirement = FileGV
        self.types.append("layer")


class ComponentClusterSupervoxel(ComponentCluster):
    """Layer-wise Component that outputs spatially-varying data labels in the
    `FileID` class format and requires input in the
    `FileID` class format.
    """

    def __init__(self):
        ComponentCluster.__init__(self)
        self.input_requirement = FileID
        self.types.append("layer")
