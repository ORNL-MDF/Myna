#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Module for functions related to AdditiveFOAM scan paths"""

import pandas as pd


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
