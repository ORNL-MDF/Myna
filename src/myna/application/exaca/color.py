#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import numpy as np
import pyebsd


# Get RGB values for each orientation
def add_pyebsd_rgb_color(df, refDir=[0, 0, 1], suffix=""):

    # Get column ids for Euler angles
    ref_cols = ["phi1", "Phi", "phi2"]
    ref_cols_ids = [df.columns.get_loc(x) for x in ref_cols]

    # Calculate active rotation matrix (crystal -> sample)
    R = pyebsd.ebsd.orientation.euler_angles_to_rotation_matrix(
        df.iloc[:, ref_cols_ids[0]],
        df.iloc[:, ref_cols_ids[1]],
        df.iloc[:, ref_cols_ids[2]],
        conv="zxz",
    )

    # Transform from active rotation (crystal -> sample)
    # to passive rotation (sample -> crystal)
    R = np.linalg.inv(R)
    orientation = pyebsd.ebsd.orientation.IPF(R, refDir)

    # Convert passive rotation matrices (orientation) to RGB colors
    # using settings to approximate the MTEX toolbox default IPF color mapping
    color = np.full((len(orientation), 3), 255, dtype=int)
    color[:, :3] = pyebsd.ebsd.plotting.get_color_IPF(
        orientation, pwr=0.4, whitespot=[2, 1, 3]
    )

    # Set grain color
    df[f"R{suffix}"] = color[:, 0] / 255
    df[f"G{suffix}"] = color[:, 1] / 255
    df[f"B{suffix}"] = color[:, 2] / 255

    return df
