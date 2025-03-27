#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#

import os
import shutil
from myna.core.app.base import MynaApp


class CubitApp(MynaApp):
    def __init__(
        self,
        sim_type,
    ):
        super().__init__("Cubit")
        self.simulation_type = sim_type
        self.parser.add_argument(
            "--cubitpath",
            default="",
            type=str,
            help="Path to the root Cubit install directory",
        )
        self.args, _ = self.parser.parse_known_args()
        super().set_procs()
        self.update_template_path()

    def update_template_path(self):
        """Updates the template path parameter"""
        if self.args.template is None:
            template_path = os.path.join(
                os.environ["MYNA_APP_PATH"],
                "cubit",
                self.simulation_type,
                "template",
            )
            self.args.template = template_path

    def copy_template_to_dir(self, target_dir):
        """Copies the specified template directory to the specified target directory"""
        # Ensure directory structure to target exists
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        if self.args.template is not None:
            shutil.copytree(self.args.template, target_dir, dirs_exist_ok=True)
