#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of layer thickness (in meters) from databases"""

from .data import *


class LayerThickness(BuildMetadata):
    """BuildMetadata subclass for layer thickness (float value, units = m)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.unit = "m"
        self.value = self.value_from_database()
