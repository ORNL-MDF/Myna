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
import shutil
from myna.core.app.base import MynaApp


class CubitApp(MynaApp):
    """Defines Myna application behavior for Cubit&reg;-based applications. Cubit&reg;
    is a toolkit for geometry and mesh generation developed by Sandia National
    Laboratories: https://cubit.sandia.gov/
    """

    def __init__(self, app_type="cubit", class_name=None):
        super().__init__(app_type, class_name)
        self.simulation_type = app_type if class_name is None else class_name
        self.parser.add_argument(
            "--cubitpath",
            default=None,
            type=str,
            help="Path to the root Cubit install directory",
        )
        self.parse_known_args()

        # Check that all needed executables are accessible. This overrides the
        # assumed behavior that each app only has one executable passed through the
        # `--exec` argument, because the user passes a Cubit install path
        path_prefix = ""
        if self.args.cubitpath is not None:
            path_prefix = os.path.join(self.args.cubitpath, "bin")
        self.exe_psculpt = os.path.join(path_prefix, "psculpt")
        self.exe_epu = os.path.join(path_prefix, "epu")
        original_executable_arg = self.args.exec
        for executable in [self.exe_psculpt, self.exe_epu]:
            self.args.exec = executable
            self.validate_executable(executable)
        # Set original value back to exec commented out since it is ignored
        if original_executable_arg is not None:
            self.args.exec = (
                f"# (ignored by {self.name}/{self.simulation_type} app) "
                + original_executable_arg
            )
        else:
            self.args.exec = original_executable_arg

    def copy_template_to_dir(self, target_dir):
        """Copies the specified template directory to the specified target directory"""
        # Ensure directory structure to target exists
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        if self.args.template is not None:
            shutil.copytree(self.args.template, target_dir, dirs_exist_ok=True)
