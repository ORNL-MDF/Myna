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


class NetCDF4Dataset:
    """Class to load and calculate NetCDF4 mesh properties relevant to the Deer app.

    Assumes that the NetCDF4 file was generated by Cubit/Sculpt. See Myna's
    cubit/vtk_to_exodus_region app output for an example.
    """

    def __init__(self, data_file):
        """Load the mesh and calculate basic properties.

        Args:
            data_file: (str) path to NetCDF data file to load
        """
        try:
            from netCDF4 import Dataset  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "Myna deer app requires `pip install .[deer]` optional dependencies!"
            ) from exc

        self.data_file = data_file
        with Dataset(self.data_file) as mesh:
            self.set_dimensions(mesh)
            self.set_n_blocks(mesh)
            self.set_max_block_number(mesh)
            self.set_euler_angles(mesh)
            self.set_filled_block_numbers(mesh)

    def set_dimensions(self, mesh):
        """Calculates the coordinate dimensions of the `netCDF4.Dataset` object and
        sets the self.bounds, `shape = (3,)`), and self.range, (`shape = (3,)`)

        Args:
            mesh: `netCDF4.Dataset` object
        """
        coordx = mesh.variables["coordx"]
        coordy = mesh.variables["coordy"]
        coordz = mesh.variables["coordz"]
        self.bounds = np.array(
            [
                [np.min(coordx), np.max(coordx)],
                [np.min(coordy), np.max(coordy)],
                [np.min(coordz), np.max(coordz)],
            ]
        )
        self.range = [
            float(self.bounds[0, 1] - self.bounds[0, 0]),
            float(self.bounds[1, 1] - self.bounds[1, 0]),
            float(self.bounds[2, 1] - self.bounds[2, 0]),
        ]

    def set_n_blocks(self, mesh):
        """Calculates the number of blocks in the `netCDF4.Dataset` object

        Args:
            mesh: `netCDF4.Dataset` object
        """
        self.n_blocks = int(mesh.dimensions["num_el_blk"].size)

    def set_max_block_number(self, mesh):
        """Finds the largest block number in the `netCDF4.Dataset` object

        Args:
            mesh: `netCDF4.Dataset` object
        """

        self.max_block_number = int(np.max(mesh.variables["eb_prop1"][:].data))

    def set_euler_angles(self, mesh):
        """Extract the Euler angles describing the crystallographic orientation of each
        block to a numpy array

        Args:
            mesh: `netCDF4.Dataset` object
        """

        self.euler_angles = np.zeros((self.n_blocks, 3))
        self.euler_angles[:, 0] = mesh.variables["euler_bunge_zxz_phi1"][:].data
        self.euler_angles[:, 1] = mesh.variables["euler_bunge_zxz_Phi"][:].data
        self.euler_angles[:, 2] = mesh.variables["euler_bunge_zxz_phi2"][:].data

    def set_filled_block_numbers(self, mesh):
        """Gets the list of non-empty block indices from the mesh

        Args:
            mesh: `netCDF4.Dataset` object
        """

        self.filled_block_indices = mesh.variables["eb_prop1"][:].data - 1

    def get_full_orientation_array(self):
        """Generates the full orientation array, including empty blocks

        Returns:
            full_orientation_array: (np.array, size (max_block_number,3))
                array describing the Euler angles in Bunge ZXZ notation for all
                blocks in the mesh, including empty blocks
        """
        full_orientation_array = np.zeros((self.max_block_number, 3))
        full_orientation_array[self.filled_block_indices, :] = self.euler_angles
        return full_orientation_array
