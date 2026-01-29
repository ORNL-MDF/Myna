#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application to take an ExaCA VTK output file and convert it to an Exodus finite
element mesh that is conformal to the grain boundaries.

For example, this application can accept the output of the `exaca/microstructure_region`
and the defaults assume that use-case.

In addition to the mesh geometry information, this application outputs the following
block data in the Exodus file that can be accessed by using the `netCDF4` package to
access the `netCDF4.Dataset().variables` dictionary:

- `id_array`: Grain IDs from the ExaCA VTK file
- `euler_bunge_zxz_phi1`: Euler angle "phi1" using the Bunge (ZXZ) notation
- `euler_bunge_zxz_Phi`: Euler angle "Phi" using the Bunge (ZXZ) notation
- `euler_bunge_zxz_phi2`: Euler angle "phi2" using the Bunge (ZXZ) notation
"""

from .app import CubitVtkToExodusApp

__all__ = ["CubitVtkToExodusApp"]
