#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define subclasses for selection of region(s) of interest"""

from .component import *
from myna.core.files.file_id import *
from myna.core.files.file_region import *


class ComponentRVE(Component):
    """Build-wise Component that outputs the location of region(s) of interest
    in the `FileRegion` class format based on the required
    input of spatially-varying data in the `FileID` class format
    """

    def __init__(self):
        Component.__init__(self)
        self.input_requirement = FileID
        self.output_requirement = FileRegion


class ComponentCentroidRVE(Component):
    """Build-wise Component that outputs the location of region(s) of interest
    in the `FileRegion` class format based on the part geometry within the build
    """

    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(["part_id_map"])
        self.output_requirement = FileRegion
