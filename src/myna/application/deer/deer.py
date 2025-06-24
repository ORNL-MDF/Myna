#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the application functionality for the base `DeerApp`, which should be
inherited by all Myna Component applications in this module."""
import os
import shutil
from myna.core.app.base import MynaApp


class DeerApp(MynaApp):
    """Myna application defining the shared functionality accessible to all Deer-based
    simulation types."""

    def __init__(
        self,
        sim_type,
    ):
        super().__init__("Deer")
        self.simulation_type = sim_type
        self.parser.add_argument(
            "--moosepath",
            default=None,
            type=str,
            help="Path to the root Moose install directory",
        )
        self.parse_known_args()
        self.update_template_path()

    def update_template_path(self):
        """Updates the template path parameter"""
        if self.args.template is None:
            template_path = os.path.join(
                os.environ["MYNA_APP_PATH"],
                "deer",
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
