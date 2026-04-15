#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application to use 3DThesis to generate a 2D map of the melt pool depth
given the laser path and process conditions for a layer.
"""

from .app import ThesisDepthMapPart

__all__ = ["ThesisDepthMapPart"]
