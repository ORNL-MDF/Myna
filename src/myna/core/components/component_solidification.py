#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define subclasses for thermal simulation Components

Available subclasses:
  ComponentSolidification
  ComponentSolidificationPart
  ComponentSolidificationRegion
  ComponentSolidificationPartSTL
  ComponentSolidificationRegionSTL
  ComponentSolidificationPartReduced
  ComponentSolidificationRegionReduced
"""

from .component import Component
from myna.core.files import (
    FileGV,
    FileRegion,
    FileBuildRegion,
    FileReducedSolidification,
)

##################
# Base Component #
##################


class ComponentSolidification(Component):
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


class ComponentSolidificationPart(ComponentSolidification):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a part in the format of the class `FileGV`
    """

    def __init__(self):
        ComponentSolidification.__init__(self)
        self.types.extend(["part", "layer"])


class ComponentSolidificationRegion(ComponentSolidification):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class `FileGV`
    based on input of the region location in the format
    `FileRegion`
    """

    def __init__(self):
        ComponentSolidification.__init__(self)
        self.input_requirement = FileRegion
        self.types.extend(["part", "region", "layer"])


class ComponentSolidificationBuildRegion(ComponentSolidification):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class `FileGV`
    based on input of the region location in the format
    `FileRegion`
    """

    def __init__(self):
        ComponentSolidification.__init__(self)
        self.data_requirements.extend(["print_order"])
        self.input_requirement = FileBuildRegion
        self.types.extend(["build_region", "layer"])


############################
# STL-requiring Components #
############################


class ComponentSolidificationPartSTL(ComponentSolidificationPart):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a part in the format of the class
    `FileGV` and requires an STL file as input.
    """

    def __init__(self):
        ComponentSolidificationPart.__init__(self)
        self.data_requirements.extend(["stl"])


class ComponentSolidificationRegionSTL(ComponentSolidificationRegion):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileGV` based on input of the region location in the format
    `FileRegion`. Requires an STL file as input.
    """

    def __init__(self):
        ComponentSolidificationRegion.__init__(self)
        self.data_requirements.extend(["stl"])


#################################################
# Reduced solidification data output Components #
#################################################
class ComponentSolidificationPartReduced(ComponentSolidificationPart):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileReducedSolidification`
    """

    def __init__(self):
        ComponentSolidificationPart.__init__(self)
        self.output_requirement = FileReducedSolidification


class ComponentSolidificationRegionReduced(ComponentSolidificationRegion):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileReducedSolidification` based on input of the region location
    in the format `FileRegion`
    """

    def __init__(self):
        ComponentSolidificationRegion.__init__(self)
        self.output_requirement = FileReducedSolidification


class ComponentSolidificationRegionReducedSTL(ComponentSolidificationRegionReduced):
    """Layer-wise Component that outputs the spatial varying solidification
    characteristics for a region in the format of the class
    `FileReducedSolidification` based on input of the region location
    in the format `FileRegion` and requiring an STL.
    """

    def __init__(self):
        ComponentSolidificationRegionReduced.__init__(self)
        self.data_requirements.extend(["stl"])
