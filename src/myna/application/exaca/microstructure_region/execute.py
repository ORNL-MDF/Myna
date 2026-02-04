#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil
import subprocess
from myna.core.components import return_step_class
from .app import ExaCAMicrostructureRegion


def run_case(app, case_dir):
    """Launch the `runCase.sh` script in the template for the given case_dir

    Args:
      app: ExaCA(MynaApp) instance
      case_dir: path to the case directory to run

    Returns:
      [result_file, process]: [path to result file, subprocess instance]
    """

    # Update number of cores to use
    run_script = os.path.join(case_dir, "runCase.sh")
    with open(run_script, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        lines[i] = line.replace("{{RANKS}}", f"{app.args.np}")
    with open(run_script, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Run case using "runCase.sh" script
    process = None
    os.system(f"chmod 755 {os.path.join(case_dir, 'runCase.sh')}")
    if not app.args.batch:
        os.system(f"{os.path.join(case_dir, 'runCase.sh')}")
    else:
        command = f"{os.path.join(case_dir, 'runCase.sh')}"
        print(f"{command=}")
        process = subprocess.Popen(command, shell=True)

    result_file = os.path.join(case_dir, "exaca.vtk")
    return result_file, process


def main():
    """Main exaca/microstructure_region execution function"""

    # Create ExaCA app instance
    app = ExaCAMicrostructureRegion()

    # Get expected Myna output files
    step_name = app.step_name
    myna_files = app.settings["data"]["output_paths"][step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_obj.apply_settings(
        app.settings["steps"][int(os.environ["MYNA_STEP_INDEX"])],
        app.settings["data"],
        app.settings["myna"],
    )
    _, _, files_are_valid = step_obj.get_output_files()

    # Run ExaCA for each Myna case, as needed
    output_files = []
    processes = []
    for myna_file, case_dir, file_is_valid in zip(
        myna_files, [os.path.dirname(x) for x in myna_files], files_are_valid
    ):
        if not file_is_valid or app.args.overwrite:
            output_file, proc = run_case(app, case_dir)
            output_files.append(output_file)
            processes.append(proc)
        else:
            output_files.append(myna_file)
    if app.args.batch:
        for proc in processes:
            print(f"Waiting on {proc.pid=}")
            proc.wait()

    # Rename result files to Myna name format
    for filepath, mynafile, file_is_valid in zip(
        output_files, myna_files, files_are_valid
    ):
        if not file_is_valid and os.path.exists(filepath):
            shutil.move(filepath, mynafile)


if __name__ == "__main__":
    main()
