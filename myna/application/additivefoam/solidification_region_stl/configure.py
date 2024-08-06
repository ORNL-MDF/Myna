import os
import argparse
import sys
import subprocess
import shutil
import pandas as pd
import numpy as np
import yaml

from myna.core.workflow.load_input import load_input
import myna.application.openfoam as openfoam
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.path import convert_peregrine_scanpath


def setup_case(case_dir, app):
    settings = app.settings
    input_dir = os.path.dirname(settings["myna"]["input"])
    resource_dir = os.path.join(input_dir, "myna_resources")

    # Generate case information from RVE list
    build = settings["build"]["name"]
    part = list(settings["build"]["parts"].keys())[0]
    part_dict = settings["build"]["parts"][part]
    region = list(settings["build"]["parts"][part]["regions"].keys())[0]
    region_dict = part_dict["regions"][region]
    layer = list(region_dict["layer_data"].keys())[0]
    layer_dict = region_dict["layer_data"][layer]

    # Set directory for template mesh
    resource_template_dir = os.path.join(
        resource_dir,
        part,
        region,
        "additivefoam",
        "solidification_region_stl",
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
        "region": region,
        "coarse_mesh": app.args.coarse,
    }
    template_region_mesh_dict = {
        "rx": app.args.rx,
        "ry": app.args.ry,
        "rz": app.args.rz,
        "region_pad": app.args.region_pad,
        "depth_pad": app.args.depth_pad,
        "substrate_pad": app.args.substrate_pad,
        "refine_layer": app.args.refine_layer,
        "refine_region": app.args.refine_region,
    }
    template_stl_mesh_dict_name = "template_stl_mesh_dict.yaml"
    template_stl_mesh_dict_path = os.path.join(
        resource_template_dir, template_stl_mesh_dict_name
    )
    template_region_mesh_dict_name = "template_region_mesh_dict.yaml"
    template_region_mesh_dict_path = os.path.join(
        resource_template_dir, template_region_mesh_dict_name
    )

    # Write template STL mesh dict as needed, and if the template
    # STL mesh dict exists, then check if it matches current mesh settings
    use_existing_stl_mesh = app.copy(
        resource_template_dir, template_region_mesh_dict_path, template_stl_mesh_dict
    )

    # Write template region mesh dict as needed, and if the template region
    # mesh dict exists, then check if it matches current mesh settings
    use_existing_region_mesh = False
    if not os.path.exists(template_region_mesh_dict_path):
        with open(template_region_mesh_dict_path, "w") as f:
            yaml.dump(template_region_mesh_dict, f, default_flow_style=False)
    else:
        with open(template_region_mesh_dict_path, "r") as f:
            existing_dict = yaml.safe_load(f)
        try:
            matches = []
            for key in template_region_mesh_dict.keys():
                entry_match = template_region_mesh_dict.get(key) == existing_dict.get(
                    key
                )
                matches.append(entry_match)
            if all(matches):
                use_existing_region_mesh = True
            else:
                with open(template_region_mesh_dict_path, "w") as f:
                    yaml.dump(template_region_mesh_dict, f, default_flow_style=None)
        except:
            with open(template_region_mesh_dict_path, "w") as f:
                yaml.dump(template_region_mesh_dict, f, default_flow_style=None)

    # Set input dictionary in format required by functions
    additivefoam_input_dict = {
        "scan_path": myna_scanfile,
        "layer": layer,
        "layer_thickness": layer_thickness,
        "layer_box": [
            [
                float(region_dict["x"] - 0.5 * app.args.rx - app.args.region_pad),
                float(region_dict["y"] - 0.5 * app.args.ry - app.args.region_pad),
                float(-app.args.rz - app.args.depth_pad),
            ],
            [
                float(region_dict["x"] + 0.5 * app.args.rx + app.args.region_pad),
                float(region_dict["y"] + 0.5 * app.args.ry + app.args.region_pad),
                float(0.0),
            ],
        ],
        "region_box": [
            [
                float(region_dict["x"] - 0.5 * app.args.rx),
                float(region_dict["y"] - 0.5 * app.args.ry),
                float(-app.args.rz),
            ],
            [
                float(region_dict["x"] + 0.5 * app.args.rx),
                float(region_dict["y"] + 0.5 * app.args.ry),
                float(0.0),
            ],
        ],
        "rve_pad": [
            app.args.region_pad,
            app.args.region_pad,
            app.args.depth_pad + app.args.substrate_pad,
        ],
        "case_dir": case_dir,
        "template": {"template_dir": resource_template_dir},
        "mesh": {
            "spacing": [app.args.coarse, app.args.coarse, app.args.coarse],
            "tolerance": 1.0e-08,
            "refinement": 0,
            "refine_layer": app.args.refine_layer,
            "refine_region": app.args.refine_region + app.args.refine_layer,
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
        use_existing_region_mesh,
    )

    return


def generate(
    additivefoam_input_dict,
    myna_settings,
    use_existing_stl_mesh,
    use_existing_region_mesh,
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

    # Convert the Myna scan path file
    path_name = os.path.basename(additivefoam_input_dict["scan_path"])
    new_scan_path_file = os.path.join(template_dir, "constant", path_name)

    convert_peregrine_scanpath(
        additivefoam_input_dict["scan_path"], new_scan_path_file, power
    )

    #####################
    # Set the beam size #
    #####################
    # 1. Get heatSourceModel
    heat_source_model = (
        subprocess.check_output(
            f"foamDictionary -entry beam/heatSourceModel -value "
            + f"{template_dir}/constant/heatSourceDict",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )

    # 2. Get heatSourceModelCoeffs/dimensions
    heat_source_dimensions = (
        subprocess.check_output(
            f"foamDictionary -entry beam/{heat_source_model}Coeffs/dimensions -value "
            + f"{template_dir}/constant/heatSourceDict",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
    heat_source_dimensions = (
        heat_source_dimensions.replace("(", "").replace(")", "").strip()
    )
    heat_source_dimensions = [float(x) for x in heat_source_dimensions.split(" ")]

    # 3. Modify X- and Y-dimensions
    heat_source_dimensions[:2] = [spot_size, spot_size]
    heat_source_dimensions = [round(dim, 7) for dim in heat_source_dimensions]

    # 4. Write to file
    heat_source_dim_string = (
        str(heat_source_dimensions)
        .replace("[", "( ")
        .replace("]", " )")
        .replace(",", "")
    )
    os.system(
        f'foamDictionary -entry beam/{heat_source_model}Coeffs/dimensions -set "{heat_source_dim_string}" '
        + f"{template_dir}/constant/heatSourceDict"
    )

    ###################
    # Mesh generation #
    ###################
    rve = additivefoam_input_dict["region_box"]
    rve_pad = additivefoam_input_dict["rve_pad"]  # convert from float to XYZ list

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

    else:
        # get the bounding box information based on specified RVE
        bb_min = [
            rve[0][0] - rve_pad[0],
            rve[0][1] - rve_pad[1],
            rve[0][2] - rve_pad[2],
        ]
        bb_max = [rve[1][0] + rve_pad[0], rve[1][1] + rve_pad[1], rve[1][2]]
        bb = bb_min + bb_max
        bbDict = {"bb_min": bb_min, "bb_max": bb_max, "bb": bb}

    if not use_existing_region_mesh:
        # Slice the mesh for the given layer
        height = float(additivefoam_input_dict["layer_thickness"]) * float(
            additivefoam_input_dict["layer"]
        )
        print("height = ", height)
        openfoam.mesh.slice(template_dir, height)

        # Generate refined mesh in layer thickness
        refinement = additivefoam_input_dict["mesh"]["refine_layer"]
        refine_dict_path = os.path.join(template_dir, "system", "refineMeshDict")
        copy_path = os.path.join(template_dir, "system", "refineLayerMeshDict")
        os.system(
            f"foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir, additivefoam_input_dict["layer_box"])

        # Archive copy of the layer refinement dict
        shutil.copy(refine_dict_path, copy_path)

        # Generate refined mesh in region
        refinement = additivefoam_input_dict["mesh"]["refine_region"]
        refine_dict_path = os.path.join(template_dir, "system", "refineMeshDict")
        os.system(
            f"foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir, additivefoam_input_dict["region_box"])

    ##############################
    # Copy template to case  dir #
    ##############################
    shutil.copytree(template_dir, case_dir, dirs_exist_ok=True)

    ##############################
    # Set the start and end time #
    ##############################
    # 1. Read scan path
    df = pd.read_csv(new_scan_path_file, sep="\s+")

    # 2. Iterate through rows to determine intersection with
    # the region's bounding box
    elapsed_time = 0.0
    start_time = None
    end_time = None
    for index, row in df.iloc[1:].iterrows():
        # 2A. If scan path row is a scan vector (Pmod == 1)
        if row["Mode"] == 0:
            v = row["tParam"]
            x1 = row["X(m)"]
            y1 = row["Y(m)"]
            x0 = df.iloc[index - 1]["X(m)"]
            y0 = df.iloc[index - 1]["Y(m)"]
            xs = np.linspace(x0, x1, 1000)
            ys = np.linspace(y0, y1, 1000)
            in_region = any(
                (xs > bbDict["bb_min"][0])
                & (xs < bbDict["bb_max"][0])
                & (ys > bbDict["bb_min"][1])
                & (ys < bbDict["bb_max"][1])
            )
            if in_region:
                end_time = None
            if in_region and (start_time is None):
                start_time = elapsed_time
            elif (not in_region) and (end_time is None):
                end_time = elapsed_time
            elapsed_time += np.linalg.norm(np.array([x1 - x0, y1 - y0])) / v

        # 2B. If scan path row is a spot (Pmod == 0)
        if row["Mode"] == 1:
            elapsed_time += row["tParam"]

    # 3. If all vectors or no vectors are in the region,
    # then set the start and end time
    if start_time is None:
        start_time = 0.0
    if end_time is None:
        end_time = elapsed_time

    # 4. Set the simulation parameters:
    # - start and end times of the simulation
    # - name of initial time-step directory
    # - scan path directory
    start_time = np.round(start_time, 5)
    end_time = np.round(end_time, 5)
    os.system(
        f"foamDictionary -entry startTime -set {start_time} "
        + f"{case_dir}/system/controlDict"
    )
    os.system(
        f"foamDictionary -entry endTime -set {end_time} "
        + f"{case_dir}/system/controlDict"
    )
    os.system(
        f"foamDictionary -entry writeInterval -set {np.round(0.5 * (end_time - start_time), 5)} "
        + f"{case_dir}/system/controlDict"
    )
    shutil.move(os.path.join(case_dir, "0"), os.path.join(case_dir, f"{start_time}"))
    os.system(
        f"foamDictionary -entry beam/pathName -set"
        + f""" '"{path_name}"' """
        + f"{case_dir}/constant/heatSourceDict"
    )

    return


def main():

    # Create app instance
    app = AdditiveFOAM("solidification_region_stl")

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

    # Generate AdditiveFOAM case files for each Myna case
    output_files = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        output_files.append(setup_case(case_dir, app))


if __name__ == "__main__":
    main()
