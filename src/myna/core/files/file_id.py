#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define file format class for cluster id data"""

from .file import File, Variable


class FileID(File):
    """Define file format class for a field of integer IDs.

    Intended for use with the `myna.components.cluster` classes.
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
                name="id",
                dtype=int,
                description="arbitrary identifier corresponding to the location,"
                " originally intended for use with cluster IDs",
            ),
        ]
