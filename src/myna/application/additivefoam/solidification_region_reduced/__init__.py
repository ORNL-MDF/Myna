#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application to use AdditiveFOAM to generate solidification data in the reduced
data format given the laser path and process conditions for a layer.

Information about the part geometry is not considered. If a representation of the
part geometry is available, then consider using `solidification_region_reduced_stl`
to represent that geometry within the simulation.
"""

from .app import AdditiveFOAMRegionReduced
