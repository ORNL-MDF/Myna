#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.application.exaca import ExaCA


class ExaCAMicrostructureRegion(ExaCA):
    def __init__(self):
        super().__init__()
        self.class_name = "microstructure_region"
