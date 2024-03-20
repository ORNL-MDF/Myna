""" Subclass for thermal simulations"""

from .component import *
from myna.files.file_gv import *
from myna.files.file_region import *
from myna.files.file_reduced_solidification import *

##################
# Base Component #
##################


class ComponentThermal(Component):
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
    def __init__(self):
        ComponentThermal.__init__(self)
        self.types.extend(["part", "layer"])


class ComponentThermalRegion(ComponentThermal):
    def __init__(self):
        ComponentThermal.__init__(self)
        self.input_requirement = FileRegion
        self.types.extend(["part", "region", "layer"])


############################
# STL-requiring Components #
############################


class ComponentThermalPartSTL(ComponentThermalPart):
    def __init__(self):
        ComponentThermalPart.__init__(self)
        self.data_requirements.extend(["stl"])


class ComponentThermalRegionSTL(ComponentThermalRegion):
    def __init__(self):
        ComponentThermalRegion.__init__(self)
        self.data_requirements.extend(["stl"])


#################################################
# Reduced solidification data output Components #
#################################################
class ComponentThermalPartReducedSolidification(ComponentThermalPart):
    def __init__(self):
        ComponentThermalPart.__init__(self)
        self.output_requirement = FileReducedSolidification


class ComponentThermalRegionReducedSolidification(ComponentThermalRegion):
    def __init__(self):
        ComponentThermalRegion.__init__(self)
        self.output_requirement = FileReducedSolidification
