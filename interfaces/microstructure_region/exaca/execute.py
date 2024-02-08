import os
import shutil
import numpy as np
import glob
import json
from myna.workflow.load_input import load_input
from myna.components import return_step_class
import argparse
import sys
import yaml
import subprocess


def nested_set(dict, keys, value):
    """modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value


def run_case(case_dir, batch):
    # Run case using "runCase.sh" script
    pid = None
    os.system(f'chmod 755 {os.path.join(case_dir, "runCase.sh")}')
    if not batch:
        os.system(f'{os.path.join(case_dir, "runCase.sh")}')
    elif batch:
        command = f'{os.path.join(case_dir, "runCase.sh")}'
        print(f"{command=}")
        process = subprocess.Popen(command, shell=True)

    result_file = os.path.join(case_dir, "output", "exaca.vtk")
    return result_file, process


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch ExaCA for " + "specified input file"
    )
    parser.add_argument(
        "--batch",
        dest="batch",
        action="store_true",
        help="flag to run jobs in background",
    )
    parser.set_defaults(batch=False)
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="flag to force re-running of cases with existing output",
    )
    parser.set_defaults(overwrite=False)

    # Parse command line arguments and get Myna settings
    args = parser.parse_args(argv)
    overwrite = args.overwrite
    batch = args.batch
    settings = load_input(os.environ["MYNA_RUN_INPUT"])

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_obj.apply_settings(
        settings["steps"][int(os.environ["MYNA_STEP_INDEX"])], settings["data"]
    )
    files, exists, files_are_valid = step_obj.get_output_files()

    # Run ExaCA for each Myna case, as needed
    output_files = []
    processes = []
    for myna_file, case_dir, file_is_valid in zip(
        myna_files, [os.path.dirname(x) for x in myna_files], files_are_valid
    ):
        if not file_is_valid or overwrite:
            output_file, proc = run_case(case_dir, batch)
            output_files.append(output_file)
            processes.append(proc)
        else:
            output_files.append(myna_file)
    if batch:
        for proc in processes:
            print(f"Waiting on {proc.pid=}")
            proc.wait()

    # Rename result files to Myna name format
    for filepath, mynafile, file_is_valid in zip(
        output_files, myna_files, files_are_valid
    ):
        if not file_is_valid:
            shutil.move(filepath, mynafile)


if __name__ == "__main__":
    main(sys.argv[1:])
