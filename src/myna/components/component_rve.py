""" Subclass for microstructure simulations"""
from .component import *
from myna.files.file_id import *
from myna.files.file_region import *


class ComponentRVE(Component):
    def __init__(self):
        Component.__init__(self)
        self.input_requirement = FileID
        self.output_requirement = FileRegion
