#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Module for functions related to AdditiveFOAM scan paths"""
from pathlib import Path
import pandas as pd
import polars as pl


def convert_peregrine_scanpath(filename, export_path, power=1):
    """converts peregrine scan path units to additivefoam scan path units"""
    df = pd.read_csv(filename, sep=r"\s+")

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
            lambda x: f"{str(x).ljust(7 + len(str(x).split('.', maxsplit=1)[0]), '0')}"
        )

    # set the laser power
    df["Power(W)"] = df["Pmod"] * power

    # set spot melts with zero time to have some small dwell time
    zero_melt_filter = (df["Mode"] == 1) & (df["tParam"] == 0.0)
    df.loc[zero_melt_filter, "tParam"] = 1e-8

    # set initial spot position time to near zero
    # This is needed for timing of AdditiveFOAM (starting from 0.0)
    # compared to timing of exported HDF5 scan paths (starting from part melt time)
    df.loc[0, "tParam"] = 1e-8

    # write the converted path to a new file
    df.to_csv(
        export_path,
        columns=["Mode", "X(m)", "Y(m)", "Z(m)", "Power(W)", "tParam"],
        sep="\t",
        index=False,
    )


def write_single_line_path(
    path: str | Path,
    power: float,
    speed: float,
    start_coord: tuple = (0, 0, 0),
    end_coord: tuple = (1e-3, 1e-3, 1e-3),
):
    """Writes a single line scan path at the specified file path

    Args:
    - path: path to export the scan path
    - power: laser power, in Watts
    - speed: travel speed, in meters/second
    - start_coords: XYZ location of the starting location of the scan, in meters
    - end_coords: XYZ location of the ending location of the scan, in meters
    """
    dict = {
        "Mode": [1, 0],
        "X(m)": [start_coord[0], end_coord[0]],
        "Y(m)": [start_coord[1], end_coord[1]],
        "Z(m)": [start_coord[2], end_coord[2]],
        "Power(W)": [0.0, power],
        "tParam": [1e-6, speed],
    }
    schema = {
        "Mode": pl.Int8,
        "X(m)": pl.Float64,
        "Y(m)": pl.Float64,
        "Z(m)": pl.Float64,
        "Power(W)": pl.Float64,
        "tParam": pl.Float64,
    }
    df = pl.from_dict(dict, schema=schema)
    df.write_csv(path, separator="\t")
