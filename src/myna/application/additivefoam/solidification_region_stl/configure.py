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
import yaml

from myna.core.workflow.load_input import load_input
from myna.application import openfoam
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.path import convert_peregrine_scanpath


def setup_case(case_dir, app):
    """Create a valid AdditiveFOAM case directory based on the myna_data.yaml file"""

    # Get case settings
    settings = load_input(os.path.join(case_dir, "myna_data.yaml"))

    # Generate case information from RVE list
    build = settings["build"]["name"]
    part = list(settings["build"]["parts"].keys())[0]
    part_dict = settings["build"]["parts"][part]
    region = list(settings["build"]["parts"][part]["regions"].keys())[0]
    region_dict = part_dict["regions"][region]
    layer = list(region_dict["layer_data"].keys())[0]
    layer_dict = region_dict["layer_data"][layer]

    # Set directory for template mesh
    template_dir = app.get_region_resource_template_dir(part, region)
    template_dir_abs = os.path.abspath(template_dir)

    # Get case metadata
    myna_scanfile = layer_dict["scanpath"]["file_local"]
    layer_thickness = settings["build"]["build_data"]["layer_thickness"]["value"]
    stl_path = part_dict["stl"]["file_local"]

    # If a template STL mesh dict exists, then test match to current STL mesh dict
    template_stl_mesh_dict = {
        "build": build,
        "part": part,
        "region": region,
        "coarse_mesh": app.args.coarse,
        "stl": stl_path,
    }
    template_stl_mesh_dict_name = "template_stl_mesh_dict.yaml"
    template_stl_mesh_dict_path = os.path.join(
        template_dir_abs, template_stl_mesh_dict_name
    )
    use_existing_stl_mesh = app.has_matching_template_mesh_dict(
        template_stl_mesh_dict_path, template_stl_mesh_dict
    )
    if not use_existing_stl_mesh:
        app.copy_template_to_dir(template_dir_abs)
        with open(template_stl_mesh_dict_path, "w", encoding="utf-8") as f:
            yaml.dump(template_stl_mesh_dict, f, default_flow_style=None)

    # If a template region mesh dict exists, then test match to current region mesh dict
    template_region_mesh_dict = {
        "build": build,
        "part": part,
        "region": region,
        "rx": app.args.rx,
        "ry": app.args.ry,
        "rz": app.args.rz,
        "region_pad": app.args.pad_xy,
        "depth_pad": app.args.pad_z,
        "substrate_pad": app.args.pad_sub,
        "coarse_mesh": app.args.coarse,
        "refine_layer": app.args.refine_layer,
        "refine_region": app.args.refine_region,
    }
    template_region_mesh_dict_name = "template_region_mesh_dict.yaml"
    template_region_mesh_dict_path = os.path.join(
        template_dir_abs, template_region_mesh_dict_name
    )
    use_existing_region_mesh = app.has_matching_template_mesh_dict(
        template_region_mesh_dict_path, template_region_mesh_dict
    )
    if not use_existing_region_mesh:
        with open(template_region_mesh_dict_path, "w", encoding="utf-8") as f:
            yaml.dump(template_region_mesh_dict, f, default_flow_style=None)

    # Set bounding boxes for mesh
    layer_box = [
        [
            float(region_dict["x"] - 0.5 * app.args.rx - app.args.pad_xy),
            float(region_dict["y"] - 0.5 * app.args.ry - app.args.pad_xy),
            float(-app.args.rz - app.args.pad_z),
        ],
        [
            float(region_dict["x"] + 0.5 * app.args.rx + app.args.pad_xy),
            float(region_dict["y"] + 0.5 * app.args.ry + app.args.pad_xy),
            float(0.0),
        ],
    ]
    region_box = [
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
    ]
    rve_pad = [
        app.args.pad_xy,
        app.args.pad_xy,
        app.args.pad_z + app.args.pad_sub,
    ]

    # Convert the Myna scan path file
    path_name = os.path.basename(myna_scanfile)
    new_scan_path_file = os.path.join(template_dir, "constant", path_name)
    power = part_dict["laser_power"]["value"]  # W
    convert_peregrine_scanpath(myna_scanfile, new_scan_path_file, power)

    # If needed, generate AdditiveFOAM mesh in template folder
    if not use_existing_stl_mesh:

        # Preprocess the STL file
        working_stl_path = openfoam.mesh.preprocess_stl(
            template_dir, stl_path, app.args.scale
        )

        # Generate background mesh
        origin, bb_dict = openfoam.mesh.create_background_mesh(
            template_dir,
            working_stl_path,
            [app.args.coarse, app.args.coarse, app.args.coarse],
            1.0e-08,
        )
        openfoam.mesh.extract_stl_features(
            template_dir,
            working_stl_path,
            0,
            origin,
        )

        # Create mesh for part
        openfoam.mesh.create_part_mesh(
            template_dir,
            working_stl_path,
            bb_dict,
            f"mpirun -np {app.args.np}",
        )

    else:
        # get the bounding box information based on specified RVE
        bb_min = [
            region_box[0][0] - rve_pad[0],
            region_box[0][1] - rve_pad[1],
            region_box[0][2] - rve_pad[2],
        ]
        bb_max = [
            region_box[1][0] + rve_pad[0],
            region_box[1][1] + rve_pad[1],
            region_box[1][2],
        ]
        bb = bb_min + bb_max
        bb_dict = {"bb_min": bb_min, "bb_max": bb_max, "bb": bb}

    if not use_existing_region_mesh:
        # Slice the mesh for the given layer
        height = float(layer_thickness) * float(layer)
        print("height = ", height)
        openfoam.mesh.slice(template_dir, height)

        # Generate refined mesh in layer thickness
        refinement = app.args.refine_layer
        refine_dict_path = os.path.join(template_dir, "system", "refineMeshDict")
        copy_path = os.path.join(template_dir, "system", "refineLayerMeshDict")
        os.system(
            "foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir, layer_box)

        # Archive copy of the layer refinement dict
        shutil.copy(refine_dict_path, copy_path)

        # Generate refined mesh in region
        refinement = app.args.refine_region + app.args.refine_layer
        refine_dict_path = os.path.join(template_dir, "system", "refineMeshDict")
        os.system(
            "foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir, region_box)

    # Copy template to case dir and then update the case parameters
    shutil.copytree(template_dir_abs, case_dir, dirs_exist_ok=True)
    app.update_beam_spot_size(part, case_dir)
    app.update_material_properties(case_dir)
    app.update_region_start_and_end_times(case_dir, bb_dict, path_name)
    app.update_heatsource_scanfile(case_dir, path_name)

    return


def main():
    """Configure all additivefoam/solidification_region_stl case directories into
    valid AdditiveFOAM cases
    """

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
