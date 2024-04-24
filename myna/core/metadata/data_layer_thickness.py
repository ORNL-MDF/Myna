"""Define loading of layer thickness (in meters) from databases"""

from .data import *


class LayerThickness(BuildMetadata):
    """BuildMetadata subclass for layer thickness (float value, units = m)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.unit = "m"
        self.value = self.value_from_database()
