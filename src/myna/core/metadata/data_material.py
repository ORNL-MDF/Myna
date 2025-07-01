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

        Returns:
            (str) Myna-formatted material name
        """
        value = self.datatype.load(type(self))
        value = self.material_name_synonym(value)
        return value

    def material_name_format(self, material):
        """Converts an input material string to consistent format

        Args:
            material : (str) material name

        """

        material_formatted = ""
        material_formatted = material.upper()
        material_formatted = material_formatted.replace(" ", "")
        material_formatted = material_formatted.replace("-", "")
        return material_formatted

    def material_name_synonym(self, material):
        """Checks if the material name is a known synonym of Myna material names. Myna
        material names correspond to the files in the `myna.mist_material_data`
        file names.

        Args:
            material: (str) material name

        Returns:
            (str) if the given material is a synonym, then returns the Myna
            material name, otherwise returns the Myna-formatted input string
        """
        # Ensure that the string is formatted as expected
        # (all upper case, no spaces, no dashes)
        material_formatted = self.material_name_format(material)
        synonyms = {
            "IN625": [
                "INCONEL625",
            ],
            "IN718": [
                "INCONEL718",
            ],
            "SS316H": [
                "STAINLESSSTEEL316H",
                "316HSS",
                "316HSTAINLESSSTEEL",
            ],
            "SS316L": [
                "STAINLESSSTEEL316L",
                "316LSS",
                "316LSTAINLESSSTEEL",
                "316STAINLESSSTEEL",
                "STAINLESSSTEEL316",
                "316SS",
            ],
        }
        for key, item in synonyms.items():
            if material_formatted in item:
                return key

        return material_formatted
