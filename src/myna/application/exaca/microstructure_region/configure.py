#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
from myna.core.workflow.load_input import load_input
from myna.core.utils import nested_get, nested_set
import shutil
import json
import numpy as np
import polars as pl

from myna.application.exaca import ExaCA


def setup_case(
    case_dir,
    sim,
    solid_files,
    layer_thickness,
):
    # Copy template to case directory
    sim.copy_template_to_case(case_dir)

    # Get case settings and template input JSON
    myna_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
    input_file = os.path.join(case_dir, "inputs.json")
    with open(input_file, "r") as f:
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
    exaca_install_dir = os.path.dirname(os.path.dirname(shutil.which(sim.args.exec)))
    orientation_file = os.path.join(
        exaca_install_dir, "share", "ExaCA", "GrainOrientationVectors.csv"
    )
    input_settings["GrainOrientationFile"] = orientation_file

    # Set cell size
    nested_set(input_settings, ["Domain", "CellSize"], sim.args.cell_size)

    # Set layer offset
    cells_per_layer = np.ceil(layer_thickness / sim.args.cell_size)
    nested_set(input_settings, ["Domain", "LayerOffset"], cells_per_layer)

    # Set temperature files
    nested_set(input_settings, ["Domain", "NumberOfLayers"], len(solid_files))
    nested_set(input_settings, ["TemperatureData", "TemperatureFiles"], solid_files)

    # Set nucleation parameters
    nested_set(input_settings, ["Nucleation", "Density"], sim.args.nd)
    nested_set(input_settings, ["Nucleation", "MeanUndercooling"], sim.args.mu)
    nested_set(input_settings, ["Nucleation", "StDev"], sim.args.std)

    # Set substrate grain size
    nested_set(input_settings, ["Substrate", "MeanSize"], sim.args.sub_size)

    # Write updated input file to case directory
    with open(input_file, "w") as f:
        json.dump(input_settings, f, indent=2)

    # Update executable information in the run script
    run_script = os.path.join(case_dir, "runCase.sh")
    with open(run_script, "r") as f:
        lines = f.readlines()
    bin_path = os.path.dirname(shutil.which(sim.args.exec))
    exec_name = os.path.basename(sim.args.exec)
    for i, line in enumerate(lines):
        lines[i] = line.replace("{{EXACA_BIN_PATH}}", bin_path)
        lines[i] = lines[i].replace("{{EXACA_EXEC}}", exec_name)
    with open(run_script, "w") as f:
        f.writelines(lines)

    # Get analysis file settings to update slice locations
    analysis_file = os.path.join(case_dir, "analysis.json")
    with open(analysis_file, "r") as f:
        analysis_settings = json.load(f)

    # Check the X and Y bounds of the first layer's solidification data and get midpoint
    df = pl.read_csv(
        nested_get(input_settings, ["TemperatureData", "TemperatureFiles"])[0]
    )
    if df.is_empty():
        return
    xmin, xmax = [df["x"].min(), df["x"].max()]
    ymin, ymax = [df["y"].min(), df["y"].max()]
    spacing = nested_get(input_settings, ["Domain", "CellSize"])
    dx = (xmax - xmin) * 1e6 / spacing
    dy = (ymax - ymin) * 1e6 / spacing
    ind_x_mid = int(0.5 * dx)
    ind_y_mid = int(0.5 * dy)

    # Get cell index near the top-surface, but not at the top surface
    dz = nested_get(input_settings, ["Domain", "NumberOfLayers"]) * nested_get(
        input_settings, ["Domain", "LayerOffset"]
    )
    ind_z_mid = int(0.8 * dz)

    # Set slice locations
    nested_set(analysis_settings, ["Regions", "XY", "zBounds"], [ind_z_mid, ind_z_mid])
    nested_set(analysis_settings, ["Regions", "XZ", "yBounds"], [ind_y_mid, ind_y_mid])
    nested_set(analysis_settings, ["Regions", "YZ", "xBounds"], [ind_x_mid, ind_x_mid])

    # Write updated analysis file to case directory
    with open(analysis_file, "w") as f:
        json.dump(analysis_settings, f, indent=2)

    return


def main():
    # Create ExaCA instance
    app = ExaCA()
    app.class_name = "microstructure_region"
    app.__init__()

    # Get expected Myna output files
    settings = app.settings
    myna_files = settings["data"]["output_paths"][app.step_name]

    # Get solidification data from previous step
    myna_solid_files = settings["data"]["output_paths"][app.last_step_name]
    solid_file_sets = []
    for part in settings["data"]["build"]["parts"]:
        p = settings["data"]["build"]["parts"][part]
        for region in p["regions"]:
            id_str = os.path.join(part, region)
            file_set = sorted([x for x in myna_solid_files if id_str in x])
            solid_file_sets.append(file_set)

    # Get layer thickness in microns
    layer_thickness = (
        1e6 * settings["data"]["build"]["build_data"]["layer_thickness"]["value"]
    )

    # Generate AdditiveFOAM case files for each Myna case
    output_files = []
    for case_dir, solid_files in zip(
        [os.path.dirname(x) for x in myna_files], solid_file_sets
    ):
        # Configure case
        output_files.append(
            setup_case(
                case_dir,
                app,
                solid_files,
                layer_thickness,
            )
        )


if __name__ == "__main__":
    main()
