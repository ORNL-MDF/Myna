#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Execute script wrapper for openfoam/mesh_part_vtk."""

from myna.application.openfoam.mesh_part_vtk.app import OpenFOAMMeshPartVTK


def execute():
    """Execute all case directories."""
    app = OpenFOAMMeshPartVTK()
    app.execute()


if __name__ == "__main__":
    execute()
