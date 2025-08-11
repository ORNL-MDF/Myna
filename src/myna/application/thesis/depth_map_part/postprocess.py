#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import glob
import pandas as pd
from myna.application.thesis import read_parameter, Thesis


def main():
    """Execute the configured 3DThesis cases for the Myna workflow"""

    # Set up simulation object
    sim = Thesis(
        "depth_map_part",
        output_suffix=".Solidification",
    )

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Post-process results to convert to Myna format
    for mynafile in myna_files:

        # Get list of result file(s), accounting for MPI ranks
        case_directory = os.path.dirname(mynafile)
        case_input_file = os.path.join(case_directory, "ParamInput.txt")
        output_name = read_parameter(case_input_file, "Name")[0]
        result_file_pattern = os.path.join(
            case_directory, "Data", f"{output_name}{sim.output_suffix}.Final*.csv"
        )
        output_files = sorted(glob.glob(result_file_pattern))
        for i, filepath in enumerate(output_files):
            df = pd.read_csv(filepath)
            df = df[df["z"] == df["z"].max()]
            df["x (m)"] = df["x"]
            df["y (m)"] = df["y"]
            df["depth (m)"] = df["depth"]
            df = df[["x (m)", "y (m)", "depth (m)"]]
            if i == 0:
                df_all = df.copy()
            else:
                df_all = pd.concat([df_all, df])
        df_all.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main()
