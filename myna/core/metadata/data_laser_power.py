"""Define loading of laser power (in Watts) from databases"""

from .data import *


class LaserPower(PartMetadata):
    """PartMetadata subclass for laser power (float value, units = W)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, part):
        PartMetadata.__init__(self, datatype, part)
        self.unit = "W"
        self.value = self.value_from_database()
