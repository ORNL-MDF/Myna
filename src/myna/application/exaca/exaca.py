#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.app.base import MynaApp


class ExaCA(MynaApp):
    def __init__(self):
        super().__init__()
        self.app_type = "exaca"

    def parse_shared_arguments(self):
        """Setup ExaCA-specific inputs"""
        self.register_argument(
            "--cell-size", type=float, help="(float) ExaCA cell size in microns"
        )
        self.register_argument(
            "--nd",
            type=float,
            default=1,
            help="(float) Multiplier for nucleation density, 10^(12) * nd)",
        )
        self.register_argument(
            "--mu",
            type=float,
            default=10,
            help="(float) Critical undercooling mean temperature "
            + "for nucleation, in Kelvin",
        )
        self.register_argument(
            "--std",
            type=float,
            default=2,
            help="(float) Standard deviation for undercooling, in Kelvin",
        )
        self.register_argument(
            "--sub-size",
            type=float,
            default=12.5,
            help="(float) Grain size of substrate, in microns",
        )

    def parse_configure_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self.validate_executable("ExaCA")
        if self.args.exec is None:
            self.args.exec = "ExaCA"

    def parse_execute_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self.validate_executable("ExaCA")
        if self.args.exec is None:
            self.args.exec = "ExaCA"

    def parse_postprocess_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
