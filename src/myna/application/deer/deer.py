#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the application functionality for the base `DeerApp`, which should be
inherited by all Myna Component applications in this module."""

from myna.core.app.base import MynaApp


class DeerApp(MynaApp):
    """Myna application defining the shared functionality accessible to all Deer-based
    simulation types."""

    def __init__(self):
        super().__init__()
        self.app_type = "deer"

    def parse_shared_arguments(self):
        self.register_argument(
            "--deer-bin",
            default="deer-opt",
            type=str,
            help="(str) DEER executable",
        )
        self.register_argument(
            "--moosepath",
            default=None,
            type=str,
            help="Path to the root Moose install directory",
        )

    def register_configure_arguments(self):
        self.parse_shared_arguments()

    def register_execute_arguments(self):
        self.parse_shared_arguments()

    @property
    def deer_bin(self):
        """Return the configured DEER executable.

        ``--exec`` remains a deprecated compatibility alias and is scheduled for
        removal in Myna 1.3.
        """
        return self.args.exec or self.args.deer_bin

    def get_required_executables(self, operation=None):
        if operation is None or operation == "execute":
            return [self.deer_bin]
        return []
