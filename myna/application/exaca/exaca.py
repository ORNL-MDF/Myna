#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.app.base import MynaApp


class ExaCA(MynaApp):

    def __init__(self, sim_type):
        super().__init__("ExaCA")
        self.simulation_type = sim_type

        # Setup ExaCA specific inputs
        self.parser.add_argument(
            "--cell-size", type=float, help="(float) ExaCA cell size in microns"
        )
        self.parser.add_argument(
            "--nd",
            type=float,
            default=1,
            help="(float) Multiplier for nucleation density, 10^(12) * nd)",
        )
        self.parser.add_argument(
            "--mu",
            type=float,
            default=10,
            help="(float) Critical undercooling mean temperature "
            + "for nucleation, in Kelvin",
        )
        self.parser.add_argument(
            "--std",
            type=float,
            default=2,
            help="(float) Standard deviation for undercooling, in Kelvin",
        )
        self.parser.add_argument(
            "--sub-size",
            type=float,
            default=12.5,
            help="(float) Grain size of substrate, in microns",
        )

        self.args = self.parser.parse_args()

        super().check_exe(
            "ExaCA",
        )

        super().set_template_path("exaca", self.simulation_type)


def exaca_module_dependency_error_msg():
    print('!! Install "exaca" optional dependencies !!')
    raise ImportError
