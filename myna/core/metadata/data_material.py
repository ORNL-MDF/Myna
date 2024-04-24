"""Define loading of the feedstock material name from databases"""

from .data import *


class Material(BuildMetadata):
    """BuildMetadata subclass for the feedstock material name (str value, uppercase
    with no spaces)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build):
        BuildMetadata.__init__(self, datatype, build)
        self.value = self.value_from_database()

    def value_from_database(self):
        """Returns the material name from the associated file

        Returns: str
        """
        value = self.datatype.load(type(self), self.build)
        value = self.material_name_format(value)
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
