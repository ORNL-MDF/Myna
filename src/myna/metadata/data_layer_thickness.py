"""Data subclass for spot size"""

from .data import *
from .database_types import *


class LayerThickness(BuildMetadata):
    def __init__(self, datatype, build):
        BuildMetadata.__init__(self, datatype, build)
        self.unit = "m"
        self.value = self.value_from_file()

    def value_from_file(self):
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            conversion = 1e-3  # millimeters -> meters
            value = float(data["layer_thickness"] * conversion)
        return value
