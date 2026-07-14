#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Execute-stage wrapper for Condor part solidification."""

from myna.application.condor.solidification_part import CondorSolidificationPart


def execute():
    """Execute all Condor case directories."""
    CondorSolidificationPart().execute()


if __name__ == "__main__":
    execute()
