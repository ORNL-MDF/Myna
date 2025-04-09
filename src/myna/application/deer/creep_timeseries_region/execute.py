#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#

from myna.application.deer.creep_timeseries_region import CreepTimeseriesRegionDeerApp


def execute():
    """Run all deer/creep_timeseries_region case directories"""
    # Create app instance and run all cases
    app = CreepTimeseriesRegionDeerApp()
    app.run_all_cases()


if __name__ == "__main__":
    execute()
