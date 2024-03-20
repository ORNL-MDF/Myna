""" Subclass for microstructure simulations"""

from .component import *
from myna.files.file_reduced_solidification import *
from myna.files.file_vtk import *


class ComponentMicrostructure(Component):
    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(["material"])
        self.input_requirement = FileReducedSolidification
        self.output_requirement = FileVTK


class ComponentMicrostructurePart(ComponentMicrostructure):
    def __init__(self):
        ComponentMicrostructure.__init__(self)
        self.types.append("part")


class ComponentMicrostructureRegion(ComponentMicrostructurePart):
    def __init__(self):
        ComponentMicrostructurePart.__init__(self)
        self.types.append("region")
