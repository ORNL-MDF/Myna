#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
from myna.application.thesis import adjust_parameter, read_parameter
from myna.application.thesis import Thesis
import sys
import pandas as pd
import glob


def run_case(
    proc_list,
    sim,
    check_for_existing_results=True,
):
    # Update simulation threads
    settings_file = os.path.join(sim.input_dir, "Settings.txt")
    adjust_parameter(settings_file, "MaxThreads", sim.args.np)

    # Check if output file exists
    if check_for_existing_results:
        output_files = glob.glob(os.path.join(sim.input_dir, "Data", "*.csv"))
        if (len(output_files) > 0) and not sim.args.overwrite:
            print(f"{sim.input_dir} has already been simulated. Skipping.")
            return proc_list or []

    # Run Simulation
    case_directory = os.path.abspath(sim.input_dir)
    procs = proc_list or []
    procs = sim.run_thesis_case(case_directory, procs)

    return procs or []


def main(argv=None):
    # Set up simulation object
    sim = Thesis(output_suffix=".Solidification")
    sim.class_name = "solidification_part"

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Run each case
    proc_list = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        sim.set_case(case_dir, case_dir)
        proc_list = run_case(proc_list, sim)

    # Wait for any remaining processes
    for proc in proc_list:
        pid = proc.pid
        print(f"\t{pid=}: Waiting for simulation to complete")
        proc.wait()
        print(f"\t{pid=}: Simulation complete")

    # Post-process results to convert to Myna format
    for mynafile in myna_files:
        # Get list of result file(s), accounting for MPI ranks
        case_directory = os.path.dirname(mynafile)
        output_name = read_parameter(sim.input_file, "Name")[0]
        result_file_pattern = os.path.join(
            case_directory, "Data", f"{output_name}{sim.output_suffix}.Final*.csv"
        )
        output_files = sorted(glob.glob(result_file_pattern))
        for i, filepath in enumerate(output_files):
            df = pd.read_csv(filepath)
            df["x (m)"] = df["x"]
            df["y (m)"] = df["y"]
            df["G (K/m)"] = df["G"]
            df["V (m/s)"] = df["V"]
            df = df[["x (m)", "y (m)", "G (K/m)", "V (m/s)"]]
            if i == 0:
                df_all = df.copy()
            else:
                df_all = pd.concat([df_all, df])
        df_all.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main(sys.argv[1:])
