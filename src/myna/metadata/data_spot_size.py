"""Data subclass for spot size"""

from .data import *
from .database_types import *


class SpotSize(PartMetadata):
    def __init__(self, datatype, build, part):
        PartMetadata.__init__(self, datatype, build, part)
        self.unit = "mm"
        self.value = self.value_from_file()

    def value_from_file(self):
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            index = [
                ind
                for ind, x in enumerate(data["parameter_names"])
                if x == "Spot Size (mm)"
            ][0]
            value = float(data["parameter_values"][index])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns and correct accordingly.
            if value > 10:
                value = value * 1e-3

        return value
