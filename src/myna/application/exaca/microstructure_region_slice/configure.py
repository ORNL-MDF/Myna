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
import shutil
import numpy as np
from myna.core.workflow.load_input import load_input
from myna.core.utils import nested_set
from myna.application.exaca import ExaCA


def setup_case(
    app,
    case_dir,
    solid_files,
    layer_thickness,
):
    """Create a valid ExaCA `microstructure_region_slice` type simulation directory
    from `myna_data.yaml` file in the Myna case directory"""

    # Copy template to case directory
    app.copy(case_dir)

    # Get case settings and template input JSON
    myna_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
    input_file = os.path.join(case_dir, "inputs.json")
    with open(input_file, "r", encoding="utf-8") as f:
        input_settings = json.load(f)

    # Set material-specific data
    material = myna_settings["build"]["build_data"]["material"]["value"]
    material_file = os.path.join(
        os.environ["MYNA_APP_PATH"],
        "exaca",
        "materials",
        f"{material}.json",
    )
    input_settings["MaterialFileName"] = material_file

    # Set orientation file
    exaca_install_dir = os.path.dirname(os.path.dirname(shutil.which(app.args.exec)))
    orientation_file = os.path.join(
        exaca_install_dir, "share", "ExaCA", "GrainOrientationVectors.csv"
    )
    input_settings["GrainOrientationFile"] = orientation_file

    # Set cell size
    nested_set(input_settings, ["Domain", "CellSize"], app.args.cell_size)

    # Set layer offset
    cells_per_layer = np.ceil(layer_thickness / app.args.cell_size)
    nested_set(input_settings, ["Domain", "LayerOffset"], cells_per_layer)

    # Set temperature files
    nested_set(input_settings, ["Domain", "NumberOfLayers"], len(solid_files))
    nested_set(input_settings, ["TemperatureData", "TemperatureFiles"], solid_files)

    # Set nucleation parameters
    nested_set(input_settings, ["Nucleation", "Density"], app.args.nd)
    nested_set(input_settings, ["Nucleation", "MeanUndercooling"], app.args.mu)
    nested_set(input_settings, ["Nucleation", "StDev"], app.args.std)

    # Set substrate grain size
    nested_set(input_settings, ["Substrate", "MeanSize"], app.args.sub_size)

    # Write updated input file to case directory
    with open(input_file, "w", encoding="utf-8") as f:
        json.dump(input_settings, f, indent=2)

    # Update executable information in the run script
    run_script = os.path.join(case_dir, "runCase.sh")
    with open(run_script, "r", encoding="utf-8") as f:
        lines = f.readlines()
    bin_path = os.path.dirname(shutil.which(app.args.exec))
    exec_name = os.path.basename(app.args.exec)
    for i, line in enumerate(lines):
        lines[i] = line.replace("{{EXACA_BIN_PATH}}", bin_path)
        lines[i] = lines[i].replace("{{EXACA_EXEC}}", exec_name)
    with open(run_script, "w", encoding="utf-8") as f:
        f.writelines(lines)

    return


def main():
    """Main configuration functionality for exaca/microstructure_region_slice"""

    # Create ExaCA instance
    app = ExaCA(class_name="microstructure_region_slice")

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

    # Get solidification data from previous step
    myna_solid_files = app.settings["data"]["output_paths"][app.last_step_name]
    solid_file_sets = []
    for part in app.settings["data"]["build"]["parts"]:
        p = app.settings["data"]["build"]["parts"][part]
        for region in p["regions"]:
            id_str = os.path.join(part, region)
            file_set = sorted([x for x in myna_solid_files if id_str in x])
            solid_file_sets.append(file_set)

    # Get layer thickness in microns
    layer_thickness = (
        1e6 * app.settings["data"]["build"]["build_data"]["layer_thickness"]["value"]
    )

    # Generate AdditiveFOAM case files for each Myna case
    output_files = []
    for case_dir, solid_files in zip(
        [os.path.dirname(x) for x in myna_files], solid_file_sets
    ):
        # Configure case
        output_files.append(
            setup_case(
                app,
                case_dir,
                solid_files,
                layer_thickness,
            )
        )


if __name__ == "__main__":
    main()
