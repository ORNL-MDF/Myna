"""Application to take an an Exodus finite element mesh that is conformal to the grain
boundaries (assumedly a Cubit/Sculpt mesh) as an input to a
[Deer](https://github.com/Argonne-National-Laboratory/deer) simulation. The simulation
will output a `.csv` file with a times series of creep strain, in addition to the
output files specified in the Deer `case.i` file in the template.

For example, this application can accept the output of the `cubit/vtk_to_exodus_region`
and the defaults assume that use-case.

This application assumes that the following variables are available in the Exodus mesh
file. This block data in the Exodus file can be accessed by using the `netCDF4` package
to access the `netCDF4.Dataset().variables` dictionary:

- `euler_bunge_zxz_phi1`: Euler angle "phi1" using the Bunge (ZXZ) notation
- `euler_bunge_zxz_Phi`: Euler angle "Phi" using the Bunge (ZXZ) notation
- `euler_bunge_zxz_phi2`: Euler angle "phi2" using the Bunge (ZXZ) notation
"""

from .app import AdditiveFOAMRegionReduced
