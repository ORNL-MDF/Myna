#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.application.rve import RVE
import os
import polars as pl
from myna.core.workflow import config, write_input


def main():
    class RVEPartCenter(RVE):
        def __init__(self):
            super().__init__()
            self.class_name = "rve_part_center"

    app = RVEPartCenter()

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
        df = pl.read_csv(myna_file)

        # Use itertuples to iterate while preserving dtype for all columns
        # Note: using iterrows creates a pd.Series, which only has one dtype for all values
        for row in df.iter_rows(named=True):
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
