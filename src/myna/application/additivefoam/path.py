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
