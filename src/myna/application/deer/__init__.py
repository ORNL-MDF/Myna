#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application module for [Deer](https://github.com/Argonne-National-Laboratory/deer)
simulations.

Deer simulates creep deformation using a finite element crystal plasticity
model implemented in the [Moose framework](https://mooseframework.inl.gov/).
"""
from .deer import DeerApp
from .mesh import *
