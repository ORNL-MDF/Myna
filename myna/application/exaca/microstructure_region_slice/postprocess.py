#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import json
from myna.core.components import return_step_class
from myna.core.utils import nested_get
from myna.application.exaca import (
    ExaCA,
    add_rgb_to_vtk,
)


def main():

    # Create ExaCA instance
    app = ExaCA("microstructure_region_slice")

    # Get expected Myna output files
    settings = app.settings
    myna_files = settings["data"]["output_paths"][app.step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_dict = settings["steps"][int(os.environ["MYNA_STEP_INDEX"])]
    step_obj.name = list(step_dict.keys())[0]
    step_obj.apply_settings(
        step_dict[step_obj.name], settings["data"], settings["myna"]
    )
    _, _, files_are_valid = step_obj.get_output_files()

    # Open the myna file and export the RGB fields
    for myna_file, valid in zip(myna_files, files_are_valid):
        if not valid:
            continue
        else:
            # Get reference file from the inputs.json for the case
            input_file = os.path.join(os.path.dirname(myna_file), "inputs.json")
            with open(input_file, "r") as f:
                input_dict = json.load(f)
            ref_file = input_dict["GrainOrientationFile"]

            # Get VTK output file
            output_vtk = os.path.join(
                os.path.dirname(myna_file),
                nested_get(input_dict, ["Printing", "PathToOutput"]),
                nested_get(input_dict, ["Printing", "OutputFile"]) + ".vtk",
            )

            # Add RGB coloring
            export_file = output_vtk.replace(".vtk", "_rgb.vtk")
            add_rgb_to_vtk(output_vtk, export_file, ref_file)


if __name__ == "__main__":
    main()
