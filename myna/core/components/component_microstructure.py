#
# Copyright (c) 2024 Oak Ridge National Laboratory.
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

from .component import *
from myna.core.files.file_reduced_solidification import *
from myna.core.files.file_vtk import *


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
