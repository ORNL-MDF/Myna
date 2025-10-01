#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for creep data"""

from .file import File, Variable


class FileCreepTimeSeries(File):
    """File format class for creep time series data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                "strain",
                units=None,
                dtype=float,
                description="the average engineering strain of the simulated volume",
            ),
            Variable(
                "time",
                units="s",
                dtype=float,
                description="the elapsed time in the simulation",
            ),
        ]
