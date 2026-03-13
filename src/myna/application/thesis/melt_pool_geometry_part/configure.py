#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Configure script wrapper for thesis/melt_pool_geometry_part."""

from myna.application.thesis.melt_pool_geometry_part import ThesisMeltPoolGeometryPart


def configure():
    """Configure all case directories."""
    app = ThesisMeltPoolGeometryPart()
    app.configure()


if __name__ == "__main__":
    configure()
