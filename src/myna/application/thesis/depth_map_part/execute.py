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
from myna.application.thesis import adjust_parameter, Thesis


def run_case(
    proc_list,
    sim,
    check_for_existing_results=True,
):
    """Run an individual 3DThesis case"""
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


def main():
    """Execute the configured 3DThesis cases for the Myna workflow"""

    # Set up simulation object
    sim = Thesis(
        "depth_map_part",
        output_suffix=".Solidification",
    )

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
        print(f"- {pid=}: Waiting for simulation to complete")
        proc.wait()
        print(f"- {pid=}: Simulation complete")


if __name__ == "__main__":
    main()
