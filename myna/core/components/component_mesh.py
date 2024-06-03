"""Define Component subclasses for meshing operations

Available subclasses:
  ComponentMesh
"""

from .component import *
from myna.core.files.file_vtk import *


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
