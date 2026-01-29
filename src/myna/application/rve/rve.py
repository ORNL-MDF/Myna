#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application subclass for RVE selection"""

from myna.core.app.base import MynaApp


class RVE(MynaApp):
    def __init__(self):
        super().__init__()
        self.app_type = "rve"

        self.parser.add_argument(
            "--num-region",
            default=1,
            type=int,
            help="(int) number of regions to select per system (build or part)",
        )

        self.parser.add_argument(
            "--max-layers",
            default=20,
            type=int,
            help="(int) max number of layers to include in the region",
        )

        self.parse_known_args()
