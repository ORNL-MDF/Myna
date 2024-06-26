import os
from myna.core.workflow.load_input import load_input
from myna.core.utils import nested_get, nested_set
import argparse
import sys
import shutil
import json
import numpy as np
import polars as pl


def setup_case(
    case_dir,
    exec,
    template_dir,
    solid_files,
    cell_size,
    layer_thickness,
    nd,
    mu,
    std,
    sub_size,
):

    # Copy template to case directory
    shutil.copytree(template_dir, case_dir, dirs_exist_ok=True)

    # Get case settings and template input JSON
    myna_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
    input_file = os.path.join(case_dir, "inputs.json")
    with open(input_file, "r") as f:
        input_settings = json.load(f)

    # Set material-specific data
    material = myna_settings["build"]["build_data"]["material"]["value"]
    material_file = os.path.join(
        os.environ["MYNA_INSTALL_PATH"],
        "resources",
        "exaca",
        "materials",
        f"{material}.json",
    )
    input_settings["MaterialFileName"] = material_file

    # Set orientation file
    exaca_install_dir = os.path.dirname(os.path.dirname(exec))
    oreintation_file = os.path.join(
        exaca_install_dir, "share", "ExaCA", "GrainOrientationVectors.csv"
    )
    input_settings["GrainOrientationFile"] = oreintation_file

    # Set cell size
    nested_set(input_settings, ["Domain", "CellSize"], cell_size)

    # Set layer offset
    cells_per_layer = np.ceil(layer_thickness / cell_size)
    nested_set(input_settings, ["Domain", "LayerOffset"], cells_per_layer)

    # Set temperature files
    nested_set(input_settings, ["Domain", "NumberOfLayers"], len(solid_files))
    nested_set(input_settings, ["TemperatureData", "TemperatureFiles"], solid_files)

    # Set nucleation parameters
    nested_set(input_settings, ["Nucleation", "Density"], nd)
    nested_set(input_settings, ["Nucleation", "MeanUndercooling"], mu)
    nested_set(input_settings, ["Nucleation", "StDev"], std)

    # Set substrate grain size
    nested_set(input_settings, ["Substrate", "MeanSize"], sub_size)

    # Write updated input file to case directory
    with open(input_file, "w") as f:
        json.dump(input_settings, f, indent=2)

    # Update executable information in the run script
    run_script = os.path.join(case_dir, "runCase.sh")
    with open(run_script, "r") as f:
        lines = f.readlines()
    bin_path = os.path.dirname(exec)
    exec_name = os.path.basename(exec)
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


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Configure ExaCA input files for " + "specified Myna cases"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="(str) path to template, if not specified"
        + " then assume default location",
    )
    parser.add_argument("--exec", type=str, help="(str) Path to ExaCA executable")
    parser.add_argument(
        "--cell-size", type=float, help="(float) ExaCA cell size in microns"
    )
    parser.add_argument(
        "--nd",
        type=float,
        default=1,
        help="(float) Multiplier for nucleation density, 10^(12) * nd)",
    )
    parser.add_argument(
        "--mu",
        type=float,
        default=10,
        help="(float) Critical undercooling mean temperature "
        + "for nucleation, in Kelvin",
    )
    parser.add_argument(
        "--std",
        type=float,
        default=2,
        help="(float) Standard deviation for undercooling, in Kelvin",
    )
    parser.add_argument(
        "--sub-size",
        type=float,
        default=12.5,
        help="(float) Grain size of substrate, in microns",
    )

    # Parse command line arguments and get Myna settings
    args = parser.parse_args(argv)
    settings = load_input(os.environ["MYNA_RUN_INPUT"])
    template = args.template
    cell_size = args.cell_size
    nd = args.nd
    mu = args.mu
    std = args.std
    sub_size = args.sub_size
    exec = args.exec

    # Check if executable exists
    if exec is None:
        exec = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            "exaca",
            "microstructure_region",
            "ExaCA",
            "build",
            "install",
            "bin",
            "ExaCA",
        )
    if not os.path.exists(exec):
        raise Exception(f'The specified ExaCA executable "{exec}" was not found.')
    if not os.access(exec, os.X_OK):
        raise Exception(f'The specified ExaCA executable "{exec}" is not executable.')

    # Set template path
    if template is None:
        template = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            "exaca",
            "microstructure_region",
            "template",
        )
    else:
        template = os.path.abspath(template)

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Get solidification data from previous step
    last_step_name = os.environ["MYNA_LAST_STEP_NAME"]
    myna_solid_files = settings["data"]["output_paths"][last_step_name]
    solid_file_sets = []
    for part in settings["data"]["build"]["parts"]:
        p = settings["data"]["build"]["parts"][part]
        for region in p["regions"]:
            r = p["regions"][region]
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
                exec,
                template,
                solid_files,
                cell_size,
                layer_thickness,
                nd,
                mu,
                std,
                sub_size,
            )
        )


if __name__ == "__main__":
    main(sys.argv[1:])
