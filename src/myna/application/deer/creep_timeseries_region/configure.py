#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Script called during the configure stage of `~myna.core.workflow.run`"""
from myna.application.deer.creep_timeseries_region import CreepTimeseriesRegionDeerApp


def configure():
    """Configure all deer/creep_timeseries_region case directories"""
    # Create app instance and configure all cases
    app = CreepTimeseriesRegionDeerApp()
    app.configure()


if __name__ == "__main__":
    configure()
