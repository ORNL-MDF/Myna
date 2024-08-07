#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading of the beam spot size in millimeters from databases

NOTE: There are many definitions of the beam spot size that can be used,
such as D4sigma, 1/e^2, and FWHM. Currently, myna will not enforce a
particular definition, though the D4sigma spot size is preferred when
applicable.
"""

from .data import *


class SpotSize(PartMetadata):
    """BuildMetadata subclass for the beam spot size (float value, units = mm)

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, part):
        PartMetadata.__init__(self, datatype, part)
        self.unit = "mm"
        self.value = self.value_from_database()
