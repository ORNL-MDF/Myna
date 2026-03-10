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
    """Execute all cubit/vtk_to_exodus case directories."""
    app = CubitVtkToExodusApp()
    app.execute()


if __name__ == "__main__":
    execute()
