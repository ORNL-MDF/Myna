#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Execute script wrapper for thesis/solidification_part."""

from myna.application.thesis.solidification_part import ThesisSolidificationPart


def execute():
    """Execute all case directories."""
    app = ThesisSolidificationPart()
    app.execute()


if __name__ == "__main__":
    execute()
