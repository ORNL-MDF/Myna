""" Define subclasses for selection of region(s) of interest"""

from .component import *
from myna.files.file_id import *
from myna.files.file_region import *


class ComponentRVE(Component):
    """Build-wise Component that outputs the location of region(s) of interest
    in the `FileRegion` class format based on the required
    input of spatially-varying data in the `FileID` class format
    """

    def __init__(self):
        Component.__init__(self)
        self.input_requirement = FileID
        self.output_requirement = FileRegion
