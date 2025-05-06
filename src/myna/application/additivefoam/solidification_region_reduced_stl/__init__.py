"""Application to use AdditiveFOAM to generate solidification data in the reduced
data format given the laser path, process conditions, and part geometry (STL)
for a layer.

Information about the part geometry is considered by only considering the volume
within the part geometry to be in the domain. The default template considered a mixed
boundary condition (convection + radiation) to approximate heat diffusion into the
surrounding powder bed.
"""

from .app import AdditiveFOAMRegionReducedSTL
