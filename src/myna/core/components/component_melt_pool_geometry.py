#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define subclasses for melt pool geometry simulation Components

Available subclasses:
  ComponentMeltPoolGeometry
  ComponentMeltPoolGeometryPart
"""

from .component import *
from myna.core.files import FileMeltPoolGeometry

##################
# Base Component #
##################


class ComponentMeltPoolGeometry(Component):
    """Build-wise Component that outputs the domain melt pool geometry"""

    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(
            [
                "spot_size",
                "laser_power",
                "preheat",
                "material",
                "scanpath",
                "layer_thickness",
            ]
        )
        self.output_requirement = FileMeltPoolGeometry


########################################
# Part-wise and region-wise Components #
########################################


class ComponentMeltPoolGeometryPart(ComponentMeltPoolGeometry):
    """Layer-wise Component that outputs the melt pool geometry
    for a part in the format of the class `FileMeltPoolGeometry`
    """

    def __init__(self):
        ComponentMeltPoolGeometry.__init__(self)
        self.types.extend(["part", "layer"])
