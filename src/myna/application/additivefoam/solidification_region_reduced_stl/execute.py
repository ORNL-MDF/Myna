#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Script to be executed by the execute stage of `myna.core.workflow.run` to set up
a valid AdditiveFOAM case based on the specified user inputs and template
"""
from myna.application.additivefoam.solidification_region_reduced_stl.app import (
    AdditiveFOAMRegionReducedSTL,
)


def execute():
    """Configure all case directories"""
    app = AdditiveFOAMRegionReducedSTL()
    app.execute()


if __name__ == "__main__":
    execute()
