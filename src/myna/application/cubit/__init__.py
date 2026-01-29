#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""
Defines Myna application behavior for Cubit&reg;-based applications. Cubit&reg;
is a toolkit for geometry and mesh generation developed by Sandia National
Laboratories: https://cubit.sandia.gov/

Development was done with `Cubit-17.02` and behavior with other versions is untested.
"""

from .cubit import CubitApp

__all__ = ["CubitApp"]
