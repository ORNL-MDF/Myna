#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import argparse
import sys
import os
import pandas as pd
from myna.core.workflow.load_input import load_input
import numpy as np
import yaml


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Update Myna input file with region info"
    )

    # Parse cmd arguments
    args = parser.parse_args(argv)

    # Get settings
    input_file = os.environ["MYNA_RUN_INPUT"]
    settings = load_input(input_file)

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Set up regions dict if it doesn't exist
    for part in settings["data"]["build"]["parts"]:
        values = settings["data"]["build"]["parts"][part].get("regions")
        if values is None:
            settings["data"]["build"]["parts"][part]["regions"] = {}

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
            part = f"{row.part}"
            region = f"rve_{row.id}"
            settings["data"]["build"]["parts"][part]["regions"][region] = {
                "X (m)": row._1,
                "Y (m)": row._2,
                "layer_starts": row.layer_starts,
                "layer_ends": row.layer_ends,
                "layers": [
                    x for x in range(int(row.layer_starts), int(row.layer_ends) + 1)
                ],
            }

    # Update the input file
    with open(input_file, "w") as f:
        yaml.dump(settings, f, sort_keys=False, default_flow_style=None, indent=2)

    # Re-run myna_config to ensure all directories exist if there is a next step
    os.system(f"myna_config --input {input_file}")


if __name__ == "__main__":
    main(sys.argv[1:])
