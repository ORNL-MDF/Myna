#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import myna.application.thesis as thesis
import numpy as np


def get_scan_stats(scanFile):
    """Get the elapsed time of a scan path file"""

    ds = thesis.Path()
    ds.loadData(scanFile, timeName="tParam")

    # Elapsed time of scan, in seconds
    elapsed_time = ds.data["time"].max()

    # Total path distance, in millimeters
    ds.data["path distance"] = np.power(
        np.power(ds.data["xe"] - ds.data["xs"], 2)
        + np.power(ds.data["ye"] - ds.data["ys"], 2),
        0.5,
    )
    linear_distance = ds.data["path distance"].sum()
    return [elapsed_time, linear_distance]
