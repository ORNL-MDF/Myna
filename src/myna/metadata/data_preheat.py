"""Define loading of the preheat temperature (in Kelvin) from databases"""

from .data import *
from .database_types import *


class Preheat(BuildMetadata):
    """BuildMetadata subclass for the preheat temperature (float value, units = K)
    of the build plate

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build):
        BuildMetadata.__init__(self, datatype, build)
        self.unit = "K"
        self.value = self.value_from_file()

    def value_from_file(self):
        """Returns the peaheat temperature in Kelvin from the associated file

        Returns: float
        """
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            index = [
                ind
                for ind, x in enumerate(data["metadata_names"])
                if x == "Target Preheat (°C)"
            ][0]
            value = float(data["metadata_values"][index]) + 273.15
        return value
