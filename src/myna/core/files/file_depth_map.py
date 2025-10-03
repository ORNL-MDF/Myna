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


class FileDepthMap(File):
    """File format class for melt pool geometries"""

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
                name="depth",
                units="m",
                dtype=float,
                description="depth of the melt pool during the last time the point was molten",
            ),
        ]
