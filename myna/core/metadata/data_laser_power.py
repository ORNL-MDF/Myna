"""Define loading of laser power (in Watts) from databases"""

from .data import *
from .database_types import *


class LaserPower(PartMetadata):
    """PartMetadata subclass for laser power (float value, units = W)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build, part):
        PartMetadata.__init__(self, datatype, build, part)
        self.unit = "W"
        self.value = self.value_from_file()

    def value_from_file(self):
        """Returns laser power in Watts extracted from the associated file

        Returns: float
        """
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            index = [
                ind for ind, x in enumerate(data["parameter_names"]) if x == "Power (W)"
            ][0]
            value = float(data["parameter_values"][index])
        return value
