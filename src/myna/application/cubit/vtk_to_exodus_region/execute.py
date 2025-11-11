#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Script to run the execute stage of the application when called as a Myna step."""
from myna.application.cubit.vtk_to_exodus_region import CubitVtkToExodusApp


def execute():
    """Configure all cubit/vtk_to_exodus case directories"""
    # Create app instance and configure all cases
    app = CubitVtkToExodusApp()
    app.mesh_all_cases()


if __name__ == "__main__":
    execute()
