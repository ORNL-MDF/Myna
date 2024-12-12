#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil
import pandas as pd
import numpy as np
import yaml

from myna.core.workflow.load_input import load_input
import myna.application.openfoam as openfoam
from myna.application.additivefoam import (
    AdditiveFOAM,
    set_beam_size,
    set_start_and_end_times,
)
from myna.application.additivefoam.path import convert_peregrine_scanpath


def setup_case(case_dir, app):
    settings = app.settings
    input_dir = os.path.dirname(settings["myna"]["input"])
    resource_dir = os.path.join(input_dir, "myna_resources")

    # Generate case information from RVE list
    build = settings["build"]["name"]
    part = list(settings["build"]["parts"].keys())[0]
    part_dict = settings["build"]["parts"][part]
    layer = list(part_dict["layer_data"].keys())[0]
    layer_dict = part_dict["layer_data"][layer]

    # Set directory for template mesh
    resource_template_dir = os.path.join(
        resource_dir,
        part,
        "additivefoam",
        "temperature_final_part_stl",
        "template",
    )

    # Get scan path and layer thickness
    myna_scanfile = layer_dict["scanpath"]["file_local"]
    layer_thickness = settings["build"]["build_data"]["layer_thickness"]["value"]

    # Get STL file location
    stl_path = part_dict["stl"]["file_local"]

    # Set and write template background mesh dictionary
    # for checking if background mesh needs to be regenerated
    # TODO: Make sure this contains all needed fields for checking
    # if the mesh needs to be updated
    template_stl_mesh_dict = {
        "build": build,
        "part": part,
        "coarse_mesh": app.args.coarse,
    }
    template_stl_mesh_dict_name = "template_stl_mesh_dict.yaml"
    template_stl_mesh_dict_path = os.path.join(
        resource_template_dir, template_stl_mesh_dict_name
    )

    # Write template STL mesh dict as needed, and if the template
    # STL mesh dict exists, then check if it matches current mesh settings
    use_existing_stl_mesh = app.copy(
        resource_template_dir, template_stl_mesh_dict_path, template_stl_mesh_dict
    )

    # Set input dictionary in format required by functions
    additivefoam_input_dict = {
        "scan_path": myna_scanfile,
        "layer": layer,
        "layer_thickness": layer_thickness,
        "case_dir": case_dir,
        "template": {"template_dir": resource_template_dir},
        "mesh": {
            "spacing": [app.args.coarse, app.args.coarse, app.args.coarse],
            "tolerance": 1.0e-08,
            "refinement": 0,
            "refine_layer": app.args.refine_layer,
            "stl_path": stl_path,
            "convertToMeters": 1.0e-3,
            "layer_thickness": layer_thickness,
            "scaling": app.args.scale_factor,
        },
        "exe": {"nProcs": app.args.cores, "mpiArgs": f"mpirun -np {app.args.cores}"},
    }

    # Generate cases based on inputs
    generate(
        additivefoam_input_dict,
        settings,
        use_existing_stl_mesh,
    )

    return


def generate(
    additivefoam_input_dict,
    myna_settings,
    use_existing_stl_mesh,
):
    # Set paths
    case_dir = additivefoam_input_dict["case_dir"]
    template_dir = os.path.abspath(additivefoam_input_dict["template"]["template_dir"])

    # Extract the laser power and spot size from the myna settings
    part = list(myna_settings["build"]["parts"].keys())[0]
    part_dict = myna_settings["build"]["parts"][part]
    power = part_dict["laser_power"]["value"]  # W
    spot_size = (
        0.5 * part_dict["spot_size"]["value"] * 1e-3
    )  # diameter -> radius & mm -> m

    # Convert the Myna scan path file and set the beam path file name
    path_name = os.path.basename(additivefoam_input_dict["scan_path"])
    new_scan_path_file = os.path.join(template_dir, "constant", path_name)
    os.system(
        f"foamDictionary -entry beam/pathName -set"
        + f""" '"{path_name}"' """
        + f"{template_dir}/constant/heatSourceDict"
    )

    convert_peregrine_scanpath(
        additivefoam_input_dict["scan_path"], new_scan_path_file, power
    )

    #####################
    # Set the beam size #
    #####################
    set_beam_size(template_dir, spot_size, spot_size)

    ###################
    # Mesh generation #
    ###################

    # If needed, generate AdditiveFOAM mesh in template folder
    if not use_existing_stl_mesh:

        # Preprocess the STL file
        stl_path = additivefoam_input_dict["mesh"]["stl_path"]
        scale_factor = additivefoam_input_dict["mesh"]["scaling"]
        working_stl_path = openfoam.mesh.preprocess_stl(
            template_dir, stl_path, scale_factor
        )

        # Generate background mesh
        origin, bbDict = openfoam.mesh.create_background_mesh(
            template_dir,
            working_stl_path,
            additivefoam_input_dict["mesh"]["spacing"],
            additivefoam_input_dict["mesh"]["tolerance"],
        )
        openfoam.mesh.extract_stl_features(
            template_dir,
            working_stl_path,
            additivefoam_input_dict["mesh"]["refinement"],
            origin,
        )

        # Create mesh for part
        openfoam.mesh.create_part_mesh(
            template_dir,
            working_stl_path,
            bbDict,
            additivefoam_input_dict["exe"]["mpiArgs"],
        )

    ##############################
    # Copy template to case  dir #
    ##############################
    shutil.copytree(template_dir, case_dir, dirs_exist_ok=True)

    ######################################
    # Slice the mesh for the given layer #
    ######################################
    #
    height = float(additivefoam_input_dict["layer_thickness"]) * float(
        additivefoam_input_dict["layer"]
    )
    print("height = ", height)
    openfoam.mesh.slice(case_dir, height)

    ##############################
    # Set the start and end time #
    ##############################
    # 1. Read scan path into a DataFrame
    df = pd.read_csv(new_scan_path_file, sep="\s+")

    # 2. Iterate through rows to determine the elapsed time
    end_time = 0.0
    start_time = 0.0
    for index, row in df.iloc[1:].iterrows():
        # 2A. If scan path row is a scan vector (Pmod == 1)
        if row["Mode"] == 0:
            v = row["tParam"]
            x1 = row["X(m)"]
            y1 = row["Y(m)"]
            x0 = df.iloc[index - 1]["X(m)"]
            y0 = df.iloc[index - 1]["Y(m)"]
            end_time += np.linalg.norm(np.array([x1 - x0, y1 - y0])) / v

        # 2B. If scan path row is a spot (Pmod == 0)
        if row["Mode"] == 1:
            end_time += row["tParam"]

    # 3. Set the simulation start and end time:
    set_start_and_end_times(case_dir, start_time, end_time)
    return


def main():

    # Create app instance
    app = AdditiveFOAM("temperature_final_part_stl")

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

    # Generate AdditiveFOAM case files for each Myna case
    output_files = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        output_files.append(setup_case(case_dir, app))


if __name__ == "__main__":
    main()
