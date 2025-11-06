#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define Component subclasses for simulating creep behavior"""

from .component import *
from myna.core.files.file_exodus import *
from myna.core.files.file_creep import *


class ComponentCreepTimeSeries(Component):
    """Build-wise Component that outputs a time series file in the
    `FileCreepTimeSeries `class format and requires mesh input in the
    `FileExodus` class format.
    """

    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(["material"])
        self.input_requirement = FileExodus
        self.output_requirement = FileCreepTimeSeries


class ComponentCreepTimeSeriesPart(ComponentCreepTimeSeries):
    """Part-wise Component that outputs a time series file in the
    `FileCreepTimeSeries `class format and requires mesh input in the
    `FileExodus` class format.
    """

    def __init__(self):
        ComponentCreepTimeSeries.__init__(self)
        self.types.append("part")


class ComponentCreepTimeSeriesRegion(ComponentCreepTimeSeriesPart):
    """Region-wise Component that outputs a time series file in the
    `FileCreepTimeSeries `class format and requires mesh input in the
    `FileExodus` class format.
    """

    def __init__(self):
        ComponentCreepTimeSeriesPart.__init__(self)
        self.types.append("region")
