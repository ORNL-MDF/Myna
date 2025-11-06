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
import pandas as pd


def run_case(
    proc_list,
    sim,
    check_for_existing_results=True,
):
    # Update simulation threads
    settings_file = os.path.join(sim.input_dir, "Settings.txt")
    adjust_parameter(settings_file, "MaxThreads", sim.args.np)

    # Define the result file
    result_file = os.path.join(sim.input_dir, "Data", "snapshot_data.csv")

    # Check if output file exists
    if check_for_existing_results:
        if os.path.exists(result_file) and not sim.args.overwrite:
            print(f"{sim.input_dir} has already been simulated. Skipping.")
            return [result_file, proc_list]

    # Run Simulation
    case_directory = os.path.abspath(sim.input_dir)
    output_name = read_parameter(sim.input_file, "Name")[0]
    result_file = os.path.join(sim.input_dir, "Data", "snapshot_data.csv")
    procs = proc_list.copy()
    procs = sim.run_thesis_case(case_directory, procs)
    return [result_file, procs]


def main():
    # Set up simulation object
    sim = Thesis("melt_pool_geometry_part")

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Run each case
    output_files = []
    proc_list = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        sim.set_case(case_dir, case_dir)
        result_file, proc_list = run_case(proc_list, sim)
        output_files.append(result_file)

    # Wait for any remaining processes
    for proc in proc_list:
        pid = proc.pid
        print(f"\t{pid=}: Waiting for simulation to complete")
        proc.wait()
        print(f"\t{pid=}: Simulation complete")

    # Post-process results to convert to Myna format
    if output_files:
        for mynafile, snapshot_data_file in zip(myna_files, output_files):
            df = pd.read_csv(snapshot_data_file)
            df["time (s)"] = df["Time (s)"]
            df["length (m)"] = df["Length Rotated (m)"]
            df["width (m)"] = df["Width Rotated (m)"]
            df["depth (m)"] = df["Depth (m)"]
            df["x (m)"] = df["Beam X"]
            df["y (m)"] = df["Beam Y"]
            df = df[
                ["x (m)", "y (m)", "time (s)", "length (m)", "width (m)", "depth (m)"]
            ]
            df.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main()
