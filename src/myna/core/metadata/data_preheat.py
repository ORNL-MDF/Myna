#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of the preheat temperature (in Kelvin) from databases"""

from .data import *


class Preheat(BuildMetadata):
    """BuildMetadata subclass for the preheat temperature (float value, units = K)
    of the build plate

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.unit = "K"
        self.value = self.value_from_database()
