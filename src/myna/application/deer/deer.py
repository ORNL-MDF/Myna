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
        self.parser.add_argument(
            "--moosepath",
            default=None,
            type=str,
            help="Path to the root Moose install directory",
        )
        self.parse_known_args()
