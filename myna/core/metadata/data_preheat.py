"""Define loading of the preheat temperature (in Kelvin) from databases"""

from .data import *


class Preheat(BuildMetadata):
    """BuildMetadata subclass for the preheat temperature (float value, units = K)
    of the build plate

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.unit = "K"
        self.value = self.value_from_database()
