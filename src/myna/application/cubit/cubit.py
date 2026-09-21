#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the application functionality for the base `CubitApp`, which should be
inherited by all Myna Component applications in this module."""

import os
from myna.core.app.base import MynaApp


class CubitApp(MynaApp):
    """Defines Myna application behavior for Cubit&reg;-based applications. Cubit&reg;
    is a toolkit for geometry and mesh generation developed by Sandia National
    Laboratories: https://cubit.sandia.gov/
    """

    def __init__(self):
        super().__init__()
        self.app_type = "cubit"

    def parse_shared_arguments(self):
        self.register_argument(
            "--cubitpath",
            default=None,
            type=str,
            help="Path to the root Cubit install directory",
        )

    def _set_cubit_executable_paths(self):
        """Check that Cubit executables are accessible for the parsed options."""

        # Check that all needed executables are accessible. This overrides the
        # assumed behavior that each app only has one executable passed through the
        # `--exec` argument, because the user passes a Cubit install path
        path_prefix = ""
        if self.args.cubitpath is not None:
            path_prefix = os.path.join(self.args.cubitpath, "bin")
        self.exe_psculpt = os.path.join(path_prefix, "psculpt")
        self.exe_epu = os.path.join(path_prefix, "epu")

    def parse_configure_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self._set_cubit_executable_paths()

    def parse_execute_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self._set_cubit_executable_paths()
