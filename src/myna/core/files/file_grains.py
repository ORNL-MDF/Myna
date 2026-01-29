#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define grain statistics data"""

from .file import File, Variable


class FileGrainSlice(File):
    """File format class for voxelized grain ids output in VTK format"""

    def __init__(self, file):
        File.__init__(self, file)
        self.filetype = ".csv"
        self.variables = [
            Variable(
                "Mean Grain Area",
                units="m^2",
                dtype=float,
                description="mean grain area for the slice",
            ),
            Variable(
                "Nulceated Fraction",
                dtype=float,
                description="area fraction of grains that formed via nucleation rather"
                " than epitaxial growth from the substrate",
            ),
            Variable(
                "Wasserstein distance (100-Z)",
                dtype=float,
                description="Wassterstein distance between the distributions of"
                "1) the Euler angle misorientation with the (100-Z) pole for"
                " a given microstructure and 2) an isotropic reference",
            ),
        ]
