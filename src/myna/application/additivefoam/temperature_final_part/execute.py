#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
from myna.core.workflow.load_input import load_input
from myna.core.components import return_step_class
from myna.application.additivefoam import AdditiveFOAM
import subprocess
import shutil


def run_case(case_dir, cores, batch):
    # Update cores
    os.system(
        f"foamDictionary -entry numberOfSubdomains -set {cores} {case_dir}/system/decomposeParDict"
    )

    # Run case using "runCase" script
    process = None
    os.system(f'chmod 755 {os.path.join(case_dir, "runCase")}')
    if not batch:
        os.system(f'{os.path.join(case_dir, "runCase")}')
    elif batch:
        command = f'{os.path.join(case_dir, "runCase")}'
        print(f"{command=}")
        process = subprocess.Popen(command, shell=True)

    # Return resulting temperature file
    # TODO: Update to point to the top-surface slice
    latest_time = (
        subprocess.check_output(
            f"foamDictionary -entry endTime -value" + f" {case_dir}/system/controlDict",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
    result_file = os.path.join(
        case_dir, "postProcessing", "xyTopSurfaceT", latest_time, "T"
    )
    return result_file, process


def main():

    # Create app instance
    app = AdditiveFOAM("temperature_final_part_stl")

    # Parse command line arguments and get Myna settings
    args = app.parser.parse_args()
    cores = args.np
    batch = args.batch
    overwrite = args.overwrite

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = app.settings["data"]["output_paths"][step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_obj.apply_settings(
        app.settings["steps"][int(os.environ["MYNA_STEP_INDEX"])],
        app.settings["data"],
        app.settings["myna"],
    )
    files, exists, files_are_valid = step_obj.get_output_files()

    # Run AdditiveFOAM case for each Myna case, as needed
    output_files = []
    processes = []
    for myna_file, case_dir, file_is_valid in zip(
        myna_files, [os.path.dirname(x) for x in myna_files], files_are_valid
    ):
        if not file_is_valid or overwrite:
            output_file, proc = run_case(case_dir, cores, batch)
            output_files.append(output_file)
            processes.append(proc)
        else:
            output_files.append(myna_file)
    if batch:
        for proc in processes:
            if proc is not None:
                print(f"Waiting on {proc.pid=}")
                proc.wait()

    # Rename result files to Myna name format
    if not all(files_are_valid):
        for filepath, mynafile in zip(output_files, myna_files):
            shutil.move(filepath, mynafile)


if __name__ == "__main__":
    main()
