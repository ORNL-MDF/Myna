"""Define Component subclasses for classification of thermal simulations

Available subclasses:
   ComponentClassify
   ComponentClassifyThermal
   ComponentClassifySupervoxel
"""

from .component import *
from myna.core.files.file_gv import *
from myna.core.files.file_id import *


class ComponentClassify(Component):
    """Part-wise Component that outputs spatially-varying data labels in the
    `FileID` class format.
    """

    def __init__(self):
        Component.__init__(self)
        self.output_requirement = FileID
        self.types.append("part")


class ComponentClassifyThermal(ComponentClassify):
    """Layer-wise Component that outputs spatially-varying data in the
    FileID` class format and requires input from solidification
    data file of class `FileGV`.
    """

    def __init__(self):
        ComponentClassify.__init__(self)
        self.input_requirement = FileGV
        self.types.append("layer")


class ComponentClassifySupervoxel(ComponentClassify):
    """Layer-wise Component that outputs spatially-varying data labels in the
    `FileID` class format and requires input in the
    `FileID` class format.
    """

    def __init__(self):
        ComponentClassify.__init__(self)
        self.input_requirement = FileID
        self.types.append("layer")
