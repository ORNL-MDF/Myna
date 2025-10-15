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
from pathlib import Path
import polars as pl
from myna.application.thesis import adjust_parameter, read_parameter
from myna.application.thesis import Thesis


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
        # Find all path segments in the case
        pattern = str(Path(case_dir) / "path_segment_*")
        segment_dirs = sorted(glob.glob(pattern))

        # Run all segments in the case
        segment_results = []
        for segment_dir in segment_dirs:
            sim.set_case(segment_dir, segment_dir)
            result_file, proc_list = run_case(proc_list, sim)
            segment_results.append(result_file)
        output_files.append(segment_results)

    # Wait for any remaining processes
    for proc in proc_list:
        pid = proc.pid
        print(f"\t{pid=}: Waiting for simulation to complete")
        proc.wait()
        print(f"\t{pid=}: Simulation complete")

    # Set myna table schema
    myna_schema = {
        "x (m)": pl.Float64,
        "y (m)": pl.Float64,
        "time (s)": pl.Float64,
        "length (m)": pl.Float64,
        "width (m)": pl.Float64,
        "depth (m)": pl.Float64,
    }

    # Post-process results to convert to Myna format
    if output_files:
        for mynafile, segment_files in zip(myna_files, output_files):

            # Append all segment files
            thesis_to_myna_mapping = {
                "Time (s)": "time (s)",
                "Length Rotated (m)": "length (m)",
                "Width Rotated (m)": "width (m)",
                "Depth (m)": "depth (m)",
                "Beam X": "x (m)",
                "Beam Y": "y (m)",
            }
            thesis_schema = {
                k: myna_schema[v] for k, v in thesis_to_myna_mapping.items()
            }
            df_all_segments = pl.DataFrame(schema=myna_schema)
            for snapshot_data_file in segment_files:
                # Load and ensure matching of keys and dtypes
                df = pl.read_csv(snapshot_data_file, columns=list(thesis_schema))
                df = df.cast(thesis_schema)
                df = df.rename(thesis_to_myna_mapping)
                df = df.select(list(myna_schema))
                # Append to previous segments
                df_all_segments = pl.concat([df_all_segments, df])

            # Write myna file with data from all segments
            if df_all_segments.shape[0] > 0:
                df_all_segments = df_all_segments.sort(by=["time (s)"])
                df_all_segments.write_csv(mynafile)


if __name__ == "__main__":
    main()
