""" Subclass for classification of thermal simulations"""
from .component import *
from myna.files.file_gv import *
from myna.files.file_id import *


class ComponentClassify(Component):
    def __init__(self):
        Component.__init__(self)
        self.output_requirement = FileID
        self.types.append("part")


class ComponentClassifyThermal(ComponentClassify):
    def __init__(self):
        ComponentClassify.__init__(self)
        self.input_requirement = FileGV
        self.types.append("layer")


class ComponentClassifySupervoxel(ComponentClassify):
    def __init__(self):
        ComponentClassify.__init__(self)
        self.input_requirement = FileID
        self.types.append("layer")
