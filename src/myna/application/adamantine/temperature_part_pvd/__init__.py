#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Myna application for simulating the temperature of a part using adamantine for a
given layer.

Some assumptions are made:
- Given that the previous part geometry is not known, assuming that a block of material
  that is a block the `substrate_thickness` in Z-axis and bounding the
  scan path with additional `substrate_xy_padding` added in X- and Y-axes
- The block representing the substrate/previous material will be positioned to have the
  top-surface equal to the lowest Z-axis location in the scan path
- New material will be added along the scan path in blocks that are equal to the beam
  diameter in the x- and y-axes and layer thickness in the z-axis

"""
