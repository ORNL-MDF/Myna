#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class related to the temperature gradient (G) and
solidification velocity (V)
"""

from .file import File, Variable


class FileGV(File):
    """File format class for temperature gradient (G) and solidification
    velocity (V) data
    """

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
                name="g",
                units="k/m",
                dtype=float,
                description="instantaneous temperature gradient extracted at the"
                " liquidus during solidification",
            ),
            Variable(
                name="v",
                units="m/s",
                dtype=float,
                description="instantaneous solidification velocity, i.e.,"
                " liquidus isotherm velocity, extracted during solidification",
            ),
        ]
