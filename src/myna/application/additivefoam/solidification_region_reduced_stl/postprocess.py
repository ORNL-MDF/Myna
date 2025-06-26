#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Script to be executed by the postprocess stage of `myna.core.workflow.run` to compile
the AdditiveFOAM solidification data into Myna files in the format of
`FileReducedSolidification`.
"""
from myna.application.additivefoam.solidification_region_reduced_stl.app import (
    AdditiveFOAMRegionReducedSTL,
)


def postprocess():
    """Postprocess all case directories"""
    app = AdditiveFOAMRegionReducedSTL()
    app.postprocess()


if __name__ == "__main__":
    postprocess()
