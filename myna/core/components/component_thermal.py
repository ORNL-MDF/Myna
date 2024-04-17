"""Define subclasses for thermal simulation Components

Available subclasses:
  ComponentThermal
  ComponentThermalPart
  ComponentThermalRegion
  ComponentThermalPartSTL
  ComponentThermalRegionSTL
  ComponentThermalPartReducedSolidification
  ComponentThermalRegionReducedSolidification
"""

from .component import *
from myna.core.files.file_gv import *
from myna.core.files.file_region import *
from myna.core.files.file_reduced_solidification import *

##################
# Base Component #
##################


class ComponentThermal(Component):
    """Build-wise Component that outputs the spatial varying solidification G and V"""

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
        self.output_requirement = FileGV


########################################
# Part-wise and region-wise Components #
########################################


class ComponentThermalPart(ComponentThermal):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a part in the format of the class `FileGV`
    """

    def __init__(self):
        ComponentThermal.__init__(self)
        self.types.extend(["part", "layer"])


class ComponentThermalRegion(ComponentThermal):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class `FileGV`
    based on input of the region location in the format
    `FileRegion`
    """

    def __init__(self):
        ComponentThermal.__init__(self)
        self.input_requirement = FileRegion
        self.types.extend(["part", "region", "layer"])


############################
# STL-requiring Components #
############################


class ComponentThermalPartSTL(ComponentThermalPart):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a part in the format of the class
    `FileGV` and requires an STL file as input.
    """

    def __init__(self):
        ComponentThermalPart.__init__(self)
        self.data_requirements.extend(["stl"])


class ComponentThermalRegionSTL(ComponentThermalRegion):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileGV` based on input of the region location in the format
    `FileRegion`. Requires an STL file as input.
    """

    def __init__(self):
        ComponentThermalRegion.__init__(self)
        self.data_requirements.extend(["stl"])


#################################################
# Reduced solidification data output Components #
#################################################
class ComponentThermalPartReducedSolidification(ComponentThermalPart):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileReducedSolidification`
    """

    def __init__(self):
        ComponentThermalPart.__init__(self)
        self.output_requirement = FileReducedSolidification


class ComponentThermalRegionReducedSolidification(ComponentThermalRegion):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileReducedSolidification` based on input of the region location
    in the format `FileRegion`
    """

    def __init__(self):
        ComponentThermalRegion.__init__(self)
        self.output_requirement = FileReducedSolidification
