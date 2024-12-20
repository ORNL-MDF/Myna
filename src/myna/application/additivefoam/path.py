#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pandas as pd
import polars as pl


def convert_peregrine_scanpath(input_file, output_file, power=1):
    """Convert Myna scan path to an AdditiveFOAM-compatible scan path

    Args:
        input_file: Myna scan path
        output_file: AdditiveFOAM scan path to write
        power: nominal power of the laser (default 1 makes equivalent to Myna "Pmod")
    """

    data = pl.read_csv(input_file, separator="\t")
    data = data.rename(
        {
            "X(mm)": "X(mm)",
            "Y(mm)": "Y(mm)",
            "Z(mm)": "Z(mm)",
            "Pmod": "Pmod",
            "tParam": "tParam",
        }
    )
    data = data.with_columns(
        [
            (pl.col("X(mm)") / 1000.0).alias("X(m)"),  # Convert to meters
            (pl.col("Y(mm)") / 1000.0).alias("Y(m)"),  # Convert to meters
            pl.lit(0.0).alias("Z(m)"),  # Set Z to zero
            (pl.col("Pmod") * power).alias("Power"),  # Convert to Watts
        ]
    ).rename(
        {"tParam": "Parameter"}
    )  # Rename to Parameter
    data = data.select(["Mode", "X(m)", "Y(m)", "Z(m)", "Power", "Parameter"])
    data.write_csv(output_file, separator="\t")


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
