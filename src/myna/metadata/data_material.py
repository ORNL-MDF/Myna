"""Define loading of the feedstock material name from databases"""

from .data import *
from .database_types import *


class Material(BuildMetadata):
    """BuildMetadata subclass for the feedstock material name (str value, uppercase
    with no spaces)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build):
        BuildMetadata.__init__(self, datatype, build)
        self.value = self.value_from_file()

    def value_from_file(self):
        """Returns the material name from the associated file

        Returns: str
        """
        data = self.load_file_data()
        value = None
        if self.datatype == PeregrineDB:
            value = self.material_name_format(str(data["material"]))
        return value

    def material_name_format(self, mat):
        """Converts an input material string to consistent format

        Parameters
        ----------
        mat : str of material name

        """

        matOut = ""
        matOut = mat.upper()
        matOut = matOut.replace(" ", "")
        return matOut
