#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class related to the spatial distribution of temperature (T)"""

from .file import File, Variable


class FileTemperature(File):
    """File format class for temperature (T)"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                name="x",
                units="m",
                dtype=float,
                description="spatial location in x-axis",
            ),
            Variable(
                name="y",
                units="m",
                dtype=float,
                description="spatial location in y-axis",
            ),
            Variable(
                name="t",
                units="k",
                dtype=float,
                description="temperature of the location--meaning of the"
                " temperature value may vary depending on the simulation type",
            ),
        ]
