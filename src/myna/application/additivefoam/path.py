#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pandas as pd


def convert_peregrine_scanpath(filename, export_path, power=1):
    """converts peregrine scan path units to additivefoam scan path units"""
    df = pd.read_csv(filename, sep="\s+")

    # convert X & Y distances to meters
    df["X(m)"] = df["X(mm)"] * 1e-3
    df["Y(m)"] = df["Y(mm)"] * 1e-3

    # set Z value to zero
    df["Z(m)"] = df["Z(mm)"] * 0

    # format columns
    round_cols = ["X(m)", "Y(m)", "Z(m)"]
    df[round_cols] = df[round_cols].round(6)
    for col in round_cols:
        df[col] = df[col].map(
            lambda x: f'{str(x).ljust(7+len(str(x).split(".")[0]),"0")}'
        )

    # set the laser power
    df["Power(W)"] = df["Pmod"] * power

    # write the converted path to a new file
    df.to_csv(
        export_path,
        columns=["Mode", "X(m)", "Y(m)", "Z(m)", "Power(W)", "tParam"],
        sep="\t",
        index=False,
    )


def get_scanpath_bounding_box(scanpath, file_format="myna"):
    """Returns the bounding box for given scanpath file(s) in meters

    Args:
        scanpath: file or list of files of scanpaths to find the bounding box
        format: the format of the scanpath file ("myna" or "additivefoam")

    Returns:
        [[minx, miny, minz],[maxx, maxy, maxz]]
    """
    if not isinstance(scanpath, list) and isinstance(scanpath, str):
        scanpath = [scanpath]

    xmin, ymin, zmin = [1e10] * 3
    xmax, ymax, zmax = [-1e10] * 3

    if file_format.lower() == "myna":
        xcol, ycol, zcol = ["X(mm)", "Y(mm)", "Z(mm)"]
        scale = 1e-3
    elif file_format.lower() == "additivefoam":
        xcol, ycol, zcol = ["X(m)", "Y(m)", "Z(m)"]
        scale = 1

    else:
        assert file_format.lower() in ["myna", "additivefoam"]

    for f in scanpath:
        df = pd.read_csv(f, sep="\t")
        xmin = min(xmin, df[xcol].min() * scale)
        xmax = max(xmax, df[xcol].max() * scale)
        ymin = min(ymin, df[ycol].min() * scale)
        ymax = max(ymax, df[ycol].max() * scale)
        zmin = min(zmin, df[zcol].min() * scale)
        zmax = max(zmax, df[zcol].max() * scale)

    return [[xmin, ymin, zmin], [xmax, ymax, zmax]]
