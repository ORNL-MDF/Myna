#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the file format class for reduced solidification data."""

from .file import File, Variable


class FileReducedSolidification(File):
    """File format class for reduced solidification data.

    Based on a the reduced data format defined in:

    M. Rolchigo, B. Stump, J. Belak, and A. Plotkowski, "Sparse thermal data
    for cellular automata modeling of grain structure in additive
    manufacturing," Modelling Simul. Mater. Sci. Eng. 28, 065003.
    https://doi.org/10.1088/1361-651X/ab9734
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
                name="z",
                units="m",
                dtype=float,
                description="spatial location in z-axis",
            ),
            Variable(
                name="tm",
                units="s",
                dtype=float,
                description="time that the location goes above the"
                " liquidus temperature",
            ),
            Variable(
                name="ts",
                units="s",
                dtype=float,
                description="time that the location goes below"
                " the liquidus temperature",
            ),
            Variable(
                name="cr",
                units="k/s",
                dtype=float,
                description="instantaneous cooling rate at the time"
                " that the location goes below the liquidus temperature",
            ),
        ]
