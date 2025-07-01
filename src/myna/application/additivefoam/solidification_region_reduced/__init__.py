"""Application to use AdditiveFOAM to generate solidification data in the reduced
data format given the laser path and process conditions for a layer.

Information about the part geometry is not considered. If a representation of the
part geometry is available, then consider using `solidification_region_reduced_stl`
to represent that geometry within the simulation.
"""

from .app import AdditiveFOAMRegionReduced
