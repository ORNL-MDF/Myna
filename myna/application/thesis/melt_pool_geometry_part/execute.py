import autothesis.main
import autothesis.plot
import autothesis.parser as parser
import os
from myna.core.workflow.load_input import load_input
import argparse
import sys
import pandas as pd
import time
import subprocess
import glob


def run_case(
    executable,
    case_dir,
    batch,
    proc_list,
    np,
    maxproc,
    nout,
    case_input_file="ParamInput.txt",
    output_suffix="",
    overwrite=False,
    check_for_existing_results=True,
):
    # Set up simulation paths
    sim = autothesis.main.Simulation()
    sim.executable_path = executable
    sim.input_dir = case_dir
    sim.input_file = os.path.join(case_dir, case_input_file)
    sim.output_dir = case_dir

    # Update simulation threads
    settings_file = os.path.join(case_dir, "Settings.txt")
    parser.adjust_parameter(settings_file, "MaxThreads", np)

    # Define the result file
    result_file = os.path.join(case_dir, "Data", "snapshot_data.csv")

    # Check if output file exists
    if check_for_existing_results:
        if os.path.exists(result_file) and not overwrite:
            print(f"{case_dir} has already been simulated. Skipping.")
            return [result_file, proc_list]

    # Run Simulation
    case_directory = os.path.abspath(sim.input_dir)
    output_name = parser.read_parameter(sim.input_file, "Name")[0]
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
            [sim.executable_path, sim.input_file], stdout=subprocess.DEVNULL
        )
        print(f"\tRunning: {sim.executable_path} {sim.input_file}")
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
        print("Executable exists = ", os.path.exists(sim.executable_path))
        print("Input file exists = ", os.path.exists(sim.input_file))
        exit()
    os.chdir(initial_working_dir)

    return [result_file, procs]


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch autothesis for " + "specified input file"
    )
    parser.add_argument(
        "--exec", default="", type=str, help="(str) path to the executable file to use"
    )
    parser.add_argument(
        "--np",
        default=8,
        type=int,
        help="(int) processors to use per job, will "
        + "correct to the maximum available processors if "
        + "set too large",
    )
    parser.add_argument(
        "--maxproc",
        default=None,
        type=int,
        help="(int) maximum available processors for system, will "
        + "correct to the maximum available processors if "
        + "set too large",
    )
    parser.add_argument(
        "--batch", dest="batch", action="store_true", help="(flag) run jobs in parallel"
    )
    parser.add_argument(
        "--nout",
        default=1000,
        type=int,
        help="(int) number of snapshot outputs",
    )
    parser.set_defaults(batch=False)

    # Parse command line arguments
    args = parser.parse_args(argv)
    settings = load_input(os.environ["MYNA_RUN_INPUT"])
    exec = args.exec
    batch = args.batch
    np = args.np
    maxproc = args.maxproc
    nout = args.nout

    # Check if executable exists
    if exec == "":
        exec = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            "thesis",
            "solidification_part",
            "3DThesis",
            "build",
            "application",
            "3DThesis.exe",
        )
    if not os.path.exists(exec):
        raise Exception(f'3DThesis executable "{exec}" not found.')
    if not os.access(exec, os.X_OK):
        raise Exception(f'3DThesis executable "{exec}" is not executable.')

    # Get and set process information
    if maxproc is None:
        maxproc = os.cpu_count()
    np = min(os.cpu_count(), np, maxproc)

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Run autothesis for each case
    output_files = []
    proc_list = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        result_file, proc_list = run_case(
            exec, case_dir, batch, proc_list, np, maxproc, nout
        )
        output_files.append(result_file)

    # Wait for any remaining processes
    for proc in proc_list:
        pid = proc.pid
        print(f"\t{pid=}: Waiting for simulation to complete")
        proc.wait()
        print(f"\t{pid=}: Simulation complete")

    # Post-process results to convert to Myna format
    if output_files:
        for (mynafile, snapshot_data_file) in zip(myna_files, output_files):
            df = pd.read_csv(snapshot_data_file)
            df["time (s)"] = df["Time (s)"]
            df["length (m)"] = df["Length Rotated (m)"]
            df["width (m)"] = df["Width Rotated (m)"]
            df["depth (m)"] = df["Depth (m)"]
            df["x (m)"] = df["Origin X Rotated (m)"]
            df["y (m)"] = df["Origin Y Rotated (m)"]
            df = df[["x (m)", "y (m)", "time (s)", "length (m)", "width (m)", "depth (m)"]]
            df.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main(sys.argv[1:])
