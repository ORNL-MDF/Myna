#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pandas as pd
from myna.core.workflow import config, write_input
from myna.application.rve import RVE
import numpy as np


def main():
    app = RVE("rve_selection")

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = app.settings["data"]["output_paths"][step_name]

    # Set up regions dict if it doesn't exist
    for part in app.settings["data"]["build"]["parts"]:
        values = app.settings["data"]["build"]["parts"][part].get("regions")
        if values is None:
            app.settings["data"]["build"]["parts"][part]["regions"] = {}

    for myna_file in myna_files:
        # Get RVE file data
        df = pd.read_csv(
            myna_file,
            dtype={
                "id": np.int64,
                "x (m)": np.float64,
                "y (m)": np.float64,
                "layer_starts": np.int64,
                "layer_ends": np.int64,
                "part": "string",
            },
        )

        # Use itertuples to iterate while preserving dtype for all columns
        # Note: using iterrows creates a pd.Series, which only has one dtype for all values
        for row in df.itertuples(index=False):
            part = str(row["part"])
            region = f"rve_{row['id']}"
            app.settings["data"]["build"]["parts"][part]["regions"][region] = {
                "x": row["x (m)"],
                "y": row["y (m)"],
                "layer_starts": row["layer_starts"],
                "layer_ends": row["layer_ends"],
                "layers": [
                    x
                    for x in range(int(row["layer_starts"]), int(row["layer_ends"]) + 1)
                ],
            }

    # Update the input file
    write_input(app.settings, app.input_file)

    # Re-run myna_config to ensure all directories exist if there is a next step
    config.config(app.input_file)


if __name__ == "__main__":
    main()
