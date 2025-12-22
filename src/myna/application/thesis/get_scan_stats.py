#
# Copyright (c) Oak Ridge National Laboratory.
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


def _get_spot_offtime(scan_file, row_index):
    """Gets the offtime of a spot melt for the given scan path row index, returns
    None if the given row index is not a spot command with zero power."""
    ds = thesis.Path()
    ds.loadData(scan_file, timeName="tParam")
    if row_index < 0:
        row_index = len(ds.data) + row_index
    if (ds.data.at[row_index, "Mode"] == 1) and (ds.data.at[row_index, "Pmod"] == 0):
        return float(ds.data.at[row_index, "tParam"])
    return None


def get_initial_wait_time(scan_file) -> float:
    """Returns the initial wait time at the beginning of a scan path"""
    time = _get_spot_offtime(scan_file, 0)
    if time is not None:
        return float(time)
    return 0.0


def get_final_wait_time(scan_file) -> float:
    """Returns the initial wait time at the end of a scan path"""
    time = _get_spot_offtime(scan_file, -1)
    if time is not None:
        return float(time)
    return 0.0
