"""Data subclass for material name"""

from .data import *
from .database_types import *


class Material(BuildMetadata):
    def __init__(self, datatype, build):
        BuildMetadata.__init__(self, datatype, build)
        self.value = self.value_from_file()

    def value_from_file(self):
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            value = self.material_map(str(data["material"]))
        return value

    def material_map(self, mat):
        """Converts an input material string to consistent format

        Parameters
        ----------
        mat : str of material name

        """

        matOut = ""
        matOut = mat.upper()
        matOut = matOut.replace(" ", "")
        return matOut
