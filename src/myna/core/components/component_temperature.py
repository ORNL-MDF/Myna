#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define subclasses for temperature simulation Components

Available subclasses:
  ComponentTemperature
  ComponentTemperaturePart
"""

from .component import Component
from myna.core.files import FileTemperature, FilePVD

##################
# Base Component #
##################


class ComponentTemperature(Component):
    """Build-wise Component that outputs the domain temperature"""

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
        self.output_requirement = FileTemperature


########################################
# Part-wise and region-wise Components #
########################################


class ComponentTemperaturePart(ComponentTemperature):
    """Layer-wise Component that outputs the domain temperature
    for a part in the format of the class `FileTemperature`
    """

    def __init__(self):
        ComponentTemperature.__init__(self)
        self.types.extend(["part", "layer"])


class ComponentTemperaturePartPVD(ComponentTemperaturePart):
    """Layer-wise Component that outputs the domain temperature
    for a part in the format of the class `FilePVD`
    """

    def __init__(self):
        super().__init__()
        self.output_requirement = FilePVD
