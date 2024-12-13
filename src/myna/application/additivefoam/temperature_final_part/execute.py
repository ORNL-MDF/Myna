#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import subprocess
import shutil
import polars as pl
from myna.core.workflow.load_input import load_input
from myna.core.utils.nested_dict_tools import nested_find_all
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.path import (
    convert_peregrine_scanpath,
    get_scanpath_bounding_box,
)
import myna.application.openfoam as openfoam


def get_myna_file_part(myna_file):
    """Returns the string of the part component of the Myna file path

    Args:
    - myna_file: path to the Myna file

    Returns: String of the part name
    """
    return myna_file.split(os.path.sep)[-4]


def get_myna_file_layer(myna_file):
    """Returns the string of the layer component of the Myna file path

    Args:
    - myna_file: path to the Myna file

    Returns: String of the layer name
    """
    return myna_file.split(os.path.sep)[-3]


def update_parallel_cmd(app, cmd):
    """Adds mpirun and parallel arguments for running OpenFOAM applications in parallel

    Args:
        app: AdditiveFOAM(MynaApp)
        cmd: list of command arguments to update
    """
    if app.args.np > 1:
        cmd = ["mpirun", "-np", str(app.args.np)] + cmd
        cmd.append("-parallel")
    return cmd


def convert_temperature_output(case_dir, output_file):
    """Extract the top surface temperature and write as csv

    Args:
        case_dir: path to the case directory to process
        output_file: path to the output file to write
    """

    end_time = float(
        openfoam.update.foam_dict_get("endTime", f"{case_dir}/system/controlDict")
    )
    if end_time.is_integer():
        end_time = int(end_time)
    input_file = os.path.join(case_dir, f"postProcessing/topSurface/{end_time}/top.xy")

    # Read and clean data in-memory
    with open(input_file, "r", encoding="utf-8") as f:
        data = [
            line.split()
            for line in f
            if not line.strip().startswith("#") and line.strip()
        ]

    # Convert the data to a Polars DataFrame with explicit orientation
    df = pl.DataFrame(
        data, schema=["x (m)", "y (m)", "z (m)", "T (K)", "is_solid"], orient="row"
    ).with_columns(
        [
            pl.col("x (m)").cast(pl.Float64),
            pl.col("y (m)").cast(pl.Float64),
            pl.col("z (m)").cast(pl.Float64),
            pl.col("T (K)").cast(pl.Float64),
            pl.col("is_solid").cast(pl.Float64),
        ]
    )

    # Write the DataFrame to a CSV file
    df.write_csv(output_file)


def main():
    """Assembles and runs coarse heat transfer simulation for all specified layers.

    Due to each layer relying on the output of the previous layer, this app requires
    each layer to run sequentially."""

    # Create app instance
    app = AdditiveFOAM("temperature_final_part")
    app.parser.add_argument(
        "--n-cells-per-layer", type=int, default=1, help="Number of cells per layer"
    )
    app.parser.add_argument(
        "--layer-time",
        type=float,
        default=60.0,
        help="Simulation time for each layer in seconds",
    )
    app.args, _ = app.parser.parse_known_args()

    # recalculate app arguments after new argparse
    app.update_template_path()
    app.set_procs()
    app.check_exe("macroAdditiveFoam")

    # For each part, get list of directories for each layer, configure and launch
    # the corresponding simulations
    myna_files = app.settings["data"]["output_paths"][app.step_name]
    parts = list(app.settings["data"]["build"]["parts"].keys())
    for part in parts:
        # Get list of files associated with the part and extract layer numbers
        part_files = [f for f in myna_files if get_myna_file_part(f) == part]
        layers = [int(get_myna_file_layer(f)) for f in part_files]

        # Sort the lists by layer integers
        part_files = [x for _, x in sorted(zip(layers, part_files))]
        layers = sorted(layers)

        # Create a resource directory for the part's background mesh
        template_dir = os.path.abspath(app.get_part_resource_template_dir(part))
        app.copy_template_to_dir(template_dir)

        # Create the background mesh based on the bounding box of the scan path
        layer_data_dict = app.settings["data"]["build"]["parts"][part]["layer_data"]
        all_scanpaths = [
            x["file_local"] for x in nested_find_all(layer_data_dict, "scanpath")
        ]
        scanpath_box = get_scanpath_bounding_box(all_scanpaths, file_format="myna")
        layer_thickness = app.settings["data"]["build"]["build_data"][
            "layer_thickness"
        ]["value"]
        scanpath_box[0][2] = -app.args.pad_sub
        scanpath_box[1][2] = 0.0
        pad = [app.args.pad_xy, app.args.pad_xy, 0.0]
        _, _ = openfoam.mesh.create_cube_mesh(
            template_dir,
            [app.args.coarse, app.args.coarse, app.args.coarse],
            1.0e-08,
            scanpath_box,
            pad,
        )

        for index, (layer, myna_file) in enumerate(zip(layers, part_files)):
            # Get case settings
            case_dir = os.path.dirname(myna_file)
            case_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
            part = list(case_settings["build"]["parts"].keys())[0]
            part_dict = case_settings["build"]["parts"][part]
            layer_height = layer * layer_thickness

            # Copy the template case
            shutil.copytree(template_dir, case_dir, dirs_exist_ok=True)

            # Update scanpath and heat source files
            myna_scanfile = part_dict["layer_data"][str(layer)]["scanpath"][
                "file_local"
            ]
            power = case_settings["build"]["parts"][part]["laser_power"]["value"]
            path_name = os.path.basename(myna_scanfile)
            new_scan_path_file = os.path.join(case_dir, "constant", path_name)
            convert_peregrine_scanpath(myna_scanfile, new_scan_path_file, power)
            app.update_heatsource_scanfile(case_dir, path_name)
            app.update_beam_spot_size(part, case_dir)

            # TODO: Update material properties from Mist data. Cannot use default
            # Mist AdditiveFOAM file generation `app.update_material_properties()`
            # because different properties are needed

            # Update number of processors
            openfoam.update.foam_dict_set(
                "numberOfSubdomains", app.args.np, f"{case_dir}/system/decomposeParDict"
            )

            # Extrude mesh
            cells_to_extrude = app.args.n_cells_per_layer * layer
            openfoam.update.foam_dict_set(
                "nLayers", cells_to_extrude, f"{case_dir}/system/extrudeMeshDict"
            )
            openfoam.update.foam_dict_set(
                "linearDirectionCoeffs/thickness",
                layer_height,
                f"{case_dir}/system/extrudeMeshDict",
            )
            openfoam.update.foam_dict_set(
                "sourceCase",
                f'"{case_dir}"',
                f"{case_dir}/system/extrudeMeshDict",
            )
            subprocess.run(["extrudeMesh", "-case", case_dir], check=True)

            # Update times and map fields between layers
            if index == 0:
                start_time = 0
                end_time = start_time + app.args.layer_time
                openfoam.update.foam_dict_set(
                    "endTime", end_time, f"{case_dir}/system/controlDict"
                )
                app.update_start_and_end_times(case_dir, start_time, end_time, 1)
                subprocess.run(["decomposePar", "-case", case_dir], check=True)
            else:
                # Get directory for previous case
                previous_case_dir = os.path.dirname(part_files[index - 1])
                start_time = float(
                    openfoam.update.foam_dict_get(
                        "endTime",
                        os.path.join(previous_case_dir, "system", "controlDict"),
                    )
                )
                end_time = start_time + app.args.layer_time
                app.update_start_and_end_times(case_dir, start_time, end_time, 1)
                subprocess.run(["decomposePar", "-case", case_dir], check=True)
                cmd = [
                    "mapFieldsPar",
                    "-case",
                    case_dir,
                    "-mapMethod",
                    "direct",
                    "-sourceTime",
                    str(start_time),
                    previous_case_dir,
                ]
                subprocess.run(update_parallel_cmd(app, cmd), check=True)

            # Run macroAdditiveFoam
            subprocess.run(
                update_parallel_cmd(
                    app,
                    [
                        "transformPoints",
                        f"translate=(0 0 -{layer_height})",
                        "-case",
                        case_dir,
                    ],
                ),
                check=True,
            )
            subprocess.run(
                update_parallel_cmd(app, ["setFields", "-case", case_dir]), check=True
            )
            subprocess.run(
                update_parallel_cmd(app, ["macroAdditiveFoam", "-case", case_dir]),
                check=True,
            )
            subprocess.run(
                update_parallel_cmd(
                    app,
                    [
                        "transformPoints",
                        f"translate=(0 0 {layer_height})",
                        "-case",
                        case_dir,
                    ],
                ),
                check=True,
            )

            # Post-process
            subprocess.run(
                update_parallel_cmd(
                    app,
                    [
                        "postProcess",
                        "-case",
                        case_dir,
                        "-func",
                        "topSurface",
                        "-latestTime",
                    ],
                ),
                check=True,
            )
            convert_temperature_output(case_dir, myna_file)


if __name__ == "__main__":
    main()
