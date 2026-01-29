#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define Component subclasses for microstructure simulations

Available subclasses:
  ComponentMicrostructure
  ComponentMicrostructurePart
  ComponentMicrostructureRegion
"""

from .component import Component
from myna.core.files import FileReducedSolidification, FileVTK, FileGrainSlice


class ComponentMicrostructure(Component):
    """Build-wise Component that outputs a 3D microstructure file in the
    `FileVTK `class format and requires input in the
    `FileReducedSolidification` class format.
    """

    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(["material"])
        self.input_requirement = FileReducedSolidification
        self.output_requirement = FileVTK


class ComponentMicrostructurePart(ComponentMicrostructure):
    """Part-wise Component that outputs a 3D microstructure file in the
    `FileVTK` class format and requires input in the
    `FileReducedSolidification` class format.
    """

    def __init__(self):
        ComponentMicrostructure.__init__(self)
        self.types.append("part")


class ComponentMicrostructureRegion(ComponentMicrostructurePart):
    """Region-wise Component that outputs a 3D microstructure file in the
    `FileVTK` class format and requires input in the
    `FileReducedSolidification` class format.
    """

    def __init__(self):
        ComponentMicrostructurePart.__init__(self)
        self.types.append("region")


class ComponentMicrostructureRegionSlice(ComponentMicrostructureRegion):
    """Region-wise Component that outputs information on a 2D slice of the
    simulated microstructure in the `FileGrainSlice` class format and
    requires input in the `FileReducedSolidification` class format.
    """

    def __init__(self):
        ComponentMicrostructureRegion.__init__(self)
        self.output_requirement = FileGrainSlice
