import os
from myna.core.workflow.load_input import load_input
from myna.application.thesis import adjust_parameter, read_parameter
from myna.application.thesis import Thesis
import argparse
import sys
import pandas as pd
import time
import subprocess
import glob


def run_case(
    case_dir,
    proc_list,
    sim,
    check_for_existing_results=True,
):
    # Update simulation threads
    settings_file = os.path.join(case_dir, "Settings.txt")
    adjust_parameter(settings_file, "MaxThreads", np)

    # Define the result file
    result_file = os.path.join(case_dir, "Data", "snapshot_data.csv")

    # Check if output file exists
    if check_for_existing_results:
        if os.path.exists(result_file) and not overwrite:
            print(f"{case_dir} has already been simulated. Skipping.")
            return [result_file, proc_list]

    # Run Simulation
    case_directory = os.path.abspath(sim.input_dir)
    output_name = read_parameter(sim.input_file, "Name")[0]
    result_file = os.path.join(case_dir, "Data", "snapshot_data.csv")
    initial_working_dir = os.getcwd()
    os.chdir(case_directory)
    procs = proc_list.copy()
    print(f"{case_dir}:")
    print(f"\tWorking directory: {os.getcwd()}")
    try:
        # Submit job
        t0 = time.perf_counter()
        process = subprocess.Popen(
            [sim.args.exec, sim.input_file], stdout=subprocess.DEVNULL
        )
        print(f"\tRunning: {sim.args.exec} {sim.input_file}")
        print(f"\tPID: {process.pid}")

        # Check if there are enough processors available for another job
        procs_available = ((len(procs) + 2) * np) <= maxproc

        # Wait for job to finish as needed
        if batch:
            procs.append(process)
            if not procs_available:
                proc0 = procs.pop(0)
                pid = proc0.pid
                proc0.wait()
                print(f"\t{pid=}: Simulation complete")
        else:
            pid = process.pid
            process.wait()
            t1 = time.perf_counter()
            print(f"\t{pid=}: Simulation complete, run time = {t1 - t0:.1f} s")
    except Exception as e:
        print("Failed to run simulation:")
        print(e)
        print("Working directory on exit = ", os.getcwd())
        print("Executable exists = ", os.path.exists(sim.args.exec))
        print("Input file exists = ", os.path.exists(sim.input_file))
        exit()
    os.chdir(initial_working_dir)

    return [result_file, procs]


def main(argv=None):
    # Set up simulation object
    sim = Thesis("melt_pool_geometry_part", argv)

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
    main(sys.argv[1:])
