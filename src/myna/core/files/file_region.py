#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define a file format class for region of interest location data"""

from .file import File, Variable


class FileRegion(File):
    """File format class for CSV file with region of interest location data"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                name="id",
                dtype=int,
                description="integer identifier for the region",
            ),
            Variable(
                name="x",
                units="m",
                dtype=float,
                description="spatial location in x-axis of the region centroid",
            ),
            Variable(
                name="y",
                units="m",
                dtype=float,
                description="spatial location in y-axis of the region centroid",
            ),
            Variable(
                name="layer_starts",
                dtype=int,
                description="layer that region starts on",
            ),
            Variable(
                name="layer_ends",
                dtype=int,
                description="layer that region ends on",
            ),
            Variable(
                name="part",
                dtype=str,
                description="name of the part containing the region",
            ),
        ]


class FileBuildRegion(File):
    """File format class for CSV file with a rectangular region of interest location
    data in a build that can span multiple parts"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                name="id",
                dtype=int,
                description="integer identifier for the region",
            ),
            Variable(
                name="x_min",
                units="m",
                dtype=float,
                description="spatial location in x-axis of the region minimum x-bound",
            ),
            Variable(
                name="x_max",
                units="m",
                dtype=float,
                description="spatial location in x-axis of the region maximum x-bound",
            ),
            Variable(
                name="y_min",
                units="m",
                dtype=float,
                description="spatial location in y-axis of the region minimum y-bound",
            ),
            Variable(
                name="y_max",
                units="m",
                dtype=float,
                description="spatial location in y-axis of the region maximum y-bound",
            ),
            Variable(
                name="layer_starts",
                dtype=int,
                description="layer that region starts on",
            ),
            Variable(
                name="layer_ends",
                dtype=int,
                description="layer that region ends on",
            ),
            Variable(
                name="parts",
                dtype=str,
                description="'all' or part name separated by underscores, e.g., 'P1_P2'",
            ),
        ]
