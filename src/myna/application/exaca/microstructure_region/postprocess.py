#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import json
from myna.core.components import return_step_class
from myna.application.exaca import (
    ExaCA,
    add_rgb_to_vtk,
)


def main():
    """Main postprocessing functionality for exaca/microstructure_region"""

    # Create ExaCA instance
    class ExaCAMicrostructureRegion(ExaCA):
        def __init__(self):
            super().__init__()
            self.class_name = "microstructure_region"

    app = ExaCAMicrostructureRegion()

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_dict = app.settings["steps"][int(os.environ["MYNA_STEP_INDEX"])]
    step_obj.name = list(step_dict.keys())[0]
    step_obj.apply_settings(
        step_dict[step_obj.name], app.settings["data"], app.settings["myna"]
    )
    _, _, files_are_valid = step_obj.get_output_files()

    # Open the myna file and export the RGB fields
    for myna_file, valid in zip(myna_files, files_are_valid):
        if not valid:
            continue

        # Get reference file
        input_file = os.path.join(os.path.dirname(myna_file), "inputs.json")
        with open(input_file, "r", encoding="utf-8") as f:
            input_dict = json.load(f)
        ref_file = input_dict["GrainOrientationFile"]

        # Export VTK with RGB
        export_file = myna_file.replace(".vtk", "_rgb.vtk")
        add_rgb_to_vtk(myna_file, export_file, ref_file)


if __name__ == "__main__":
    main()
