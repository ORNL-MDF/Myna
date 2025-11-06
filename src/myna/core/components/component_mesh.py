#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define Component subclasses for meshing operations

Available subclasses:
  ComponentMesh
"""

from .component import *
from myna.core.files import FileVTK, FileExodus


class ComponentMesh(Component):
    """Meshing operation"""

    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(["stl", "layer_thickness"])


class ComponentPartMesh(ComponentMesh):
    """Part-wise meshing operation"""

    def __init__(self):
        ComponentMesh.__init__(self)
        self.types.append("part")


class ComponentPartMeshVTK(ComponentPartMesh):
    """Part-wise meshing operation to output a VTK-format mesh"""

    def __init__(self):
        ComponentPartMesh.__init__(self)
        self.output_requirement = FileVTK


class ComponentVTKToExodusMeshPart(Component):
    """Meshing operation on a part"""

    def __init__(self):
        Component.__init__(self)
        self.input_requirement = FileVTK
        self.output_requirement = FileExodus
        self.types.append("part")


class ComponentVTKToExodusMeshRegion(ComponentVTKToExodusMeshPart):
    """Meshing operation"""

    def __init__(self):
        ComponentVTKToExodusMeshPart.__init__(self)
        self.types.append("region")
