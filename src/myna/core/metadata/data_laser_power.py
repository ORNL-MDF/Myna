#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of laser power (in Watts) from databases"""

from .data import *


class LaserPower(PartMetadata):
    """PartMetadata subclass for laser power (float value, units = W)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, part):
        PartMetadata.__init__(self, datatype, part)
        self.unit = "W"
        self.value = self.value_from_database()
