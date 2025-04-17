#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Functionality for operating on Exodus mesh input for a Deer simulation"""

import numpy as np


def get_mesh_dimensions(exodus_mesh_file):
    """Get the dimensions of the mesh in X, Y, and Z

    Args:
        exodus_mesh_file: path to the Exodus mesh file

    Returns:
        [float(xdim), float(ydim), float(zdim)]
    """

    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise ImportError(
            'Myna deer app requires "pip install .[deer]" optional dependencies!'
        ) from exc

    with Dataset(exodus_mesh_file) as mesh:
        coordx = mesh.variables["coordx"]
        coordy = mesh.variables["coordy"]
        coordz = mesh.variables["coordz"]
        xdim = np.max(coordx) - np.min(coordx)
        ydim = np.max(coordy) - np.min(coordy)
        zdim = np.max(coordz) - np.min(coordz)
        return [float(xdim), float(ydim), float(zdim)]


def get_mesh_block_num(meshfile):
    """Get the number of blocks in the mesh file

    Args:
        exodus_mesh_file: path to the Exodus mesh file

    Returns:
        (int) number of blocks
    """

    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise ImportError(
            'Myna deer app requires "pip install .[deer]" optional dependencies!'
        ) from exc

    with Dataset(meshfile) as mesh:
        for name, dimension in mesh.dimensions.items():
            if name in ["num_el_blk"]:
                return dimension.size


def get_mesh_max_block_num(meshfile):
    """Get the maximum block ID number in the file. This can be different to the
    number of blocks in the file returned by `get_mesh_block_num()` if there are
    empty blocks.

    Args:
        exodus_mesh_file: path to the Exodus mesh file

    Returns:
        (int) maximum block id
    """

    try:
        from netCDF4 import Dataset
    except ImportError as exc:
        raise ImportError(
            'Myna deer app requires "pip install .[deer]" optional dependencies!'
        ) from exc

    with Dataset(meshfile) as mesh:
        for name, var in mesh.variables.items():
            if name in ["eb_prop1"]:
                return np.max(var[:].data)
