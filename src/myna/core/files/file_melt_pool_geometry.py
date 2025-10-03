#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class related to the spatial distribution of melt pool geometries"""

from .file import File, Variable


class FileMeltPoolGeometry(File):
    """File format class for melt pool geometries"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                name="time",
                units="s",
                dtype=float,
                description="temporal location corresponding to elapsed scan path time",
            ),
            Variable(
                name="x",
                units="m",
                dtype=float,
                description="spatial location in x-axis of the beam center at the corresponding time",
            ),
            Variable(
                name="y",
                units="m",
                dtype=float,
                description="spatial location in y-axis of the beam center at the corresponding time",
            ),
            Variable(
                name="length",
                units="m",
                dtype=float,
                description="length of the molten pool at the corresponding time",
            ),
            Variable(
                name="width",
                units="m",
                dtype=float,
                description="width of the molten pool at the corresponding time",
            ),
            Variable(
                name="depth",
                units="m",
                dtype=float,
                description="depth of the molten pool at the corresponding time",
            ),
        ]
