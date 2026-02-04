#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pandas as pd
from myna.core.components import return_step_class
from myna.application.exaca import (
    ExaCA,
    grain_id_reader,
    convert_id_to_rotation,
    get_mean_grain_area,
    get_fract_nucleated_grains,
    get_wasserstein_distance_misorientation_z,
)
import numpy as np
import subprocess
import json


def nested_set(dict, keys, value):
    """modifies a nested dictionary value given a list of keys to the nested location"""
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value


def run_case(app, case_dir):
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
    """Main functionality for the exaca/microstructure_region_slice app"""

    # Create ExaCA app instance
    class ExaCAMicrostructureRegionSlice(ExaCA):
        def __init__(self):
            super().__init__()
            self.class_name = "microstructure_region_slice"

    app = ExaCAMicrostructureRegionSlice()

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

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

    # Extract information from result files to the expected Myna 2D slice CSV format
    for filepath, myna_file, file_is_valid in zip(
        output_files, myna_files, files_are_valid
    ):
        if not file_is_valid and os.path.exists(filepath):
            # Get reference file
            input_file = os.path.join(os.path.dirname(myna_file), "inputs.json")
            with open(input_file, "r", encoding="utf-8") as f:
                input_dict = json.load(f)
            ref_file = input_dict["GrainOrientationFile"]

            # Get VTK reader for output VTK file
            reader = grain_id_reader(filepath)
            structured_points = reader.GetOutput()
            spacing = structured_points.GetSpacing()

            # Get slice from middle Z-height of data
            df = convert_id_to_rotation(reader, ref_file)
            zlist = df["Z (m)"].unique()
            slice_z_loc = 0.5 * (df["Z (m)"].max() + df["Z (m)"].min())
            slice_z_loc = zlist[np.argmin(np.abs(zlist - slice_z_loc))]
            df = df[df["Z (m)"] == slice_z_loc]

            # Grain grain statistics for the slice
            mean_grain_area = get_mean_grain_area(df, spacing[0])
            fraction_nucleated_grains = get_fract_nucleated_grains(df)

            # Calculate histograms for orientation relative to isotropic reference
            wasserstein_z = get_wasserstein_distance_misorientation_z(df, ref_file)

            # Construct output data table
            df_stats = pd.DataFrame(
                {
                    "X (m)": df["X (m)"].to_numpy(),
                    "Y (m)": df["Y (m)"].to_numpy(),
                    "Z (m)": df["Z (m)"].to_numpy(),
                    "Mean Grain Area (m^2)": np.ones_like(df["X (m)"].to_numpy())
                    * mean_grain_area,
                    "Nulceated Fraction": np.ones_like(df["X (m)"].to_numpy())
                    * fraction_nucleated_grains,
                    "Wasserstein distance (100-Z)": np.ones_like(df["X (m)"].to_numpy())
                    * wasserstein_z,
                }
            )

            # CSV grain slice data from VTK grain file
            df_stats.to_csv(myna_file, index=False)


if __name__ == "__main__":
    main()
