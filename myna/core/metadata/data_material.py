#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of the feedstock material name from databases"""

from .data import *


class Material(BuildMetadata):
    """BuildMetadata subclass for the feedstock material name (str value, uppercase
    with no spaces)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.value = self.value_from_database()

    def value_from_database(self):
        """Returns the material name from the associated file

        Returns: str
        """
        value = self.datatype.load(type(self))
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
