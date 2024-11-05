#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of part melt order from databases"""

from .data import *


class MeltOrder(BuildMetadata):
    """BuildMetadata subclass for melt order of parts, list of strings (unitless)"""

    def __init__(self, datatype):
        BuildMetadata.__init__(self, datatype)
        self.unit = ""
        self.value = self.value_from_database()
