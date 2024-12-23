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
import myna.application.openfoam as openfoam
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.path import convert_peregrine_scanpath


def setup_case(case_dir, app):
    """Create a valid AdditiveFOAM case directory based on the myna_data.yaml file"""

    # Get case settings
    settings = load_input(os.path.join(case_dir, "myna_data.yaml"))

    # Generate case information from RVE list
    build = settings["build"]["name"]
    part = list(settings["build"]["parts"].keys())[0]
    region = list(settings["build"]["parts"][part]["regions"].keys())[0]
    region_dict = settings["build"]["parts"][part]["regions"][region]
    layer = list(region_dict["layer_data"].keys())[0]

    # Set directory for template mesh
    template_dir = app.get_region_resource_template_dir(part, region)
    template_dir_abs = os.path.abspath(template_dir)

    # Get scan path and layer thickness
    myna_scanfile = region_dict["layer_data"][layer]["scanpath"]["file_local"]

    # Set template background mesh dictionary
    # for checking if background mesh needs to be regenerated
    template_mesh_dict = {
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
    template_mesh_dict_name = "template_mesh_dict.yaml"
    template_mesh_dict_path = os.path.join(template_dir, template_mesh_dict_name)

    # Copy template files if needed
    use_existing_mesh = app.has_matching_template_mesh_dict(
        template_mesh_dict_path, template_mesh_dict
    )
    if not use_existing_mesh:
        app.copy_template_to_dir(template_dir_abs)
        with open(template_mesh_dict_path, "w", encoding="utf-8") as f:
            yaml.dump(template_mesh_dict, f, default_flow_style=None)

    # Set input dictionary in format required by functions
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
    rve_pad = [app.args.pad_xy, app.args.pad_xy, app.args.pad_z + app.args.pad_sub]

    # Extract the laser power (W)
    power = settings["build"]["parts"][part]["laser_power"]["value"]

    # Convert the Myna scan path file
    path_name = os.path.basename(myna_scanfile)
    new_scan_path_file = os.path.join(template_dir_abs, "constant", path_name)
    convert_peregrine_scanpath(myna_scanfile, new_scan_path_file, power)

    # If needed, generate AdditiveFOAM mesh in template folder
    if not use_existing_mesh:

        # Generate background mesh
        _, bb_dict = openfoam.mesh.create_cube_mesh(
            template_dir,
            [app.args.coarse, app.args.coarse, app.args.coarse],
            1.0e-08,
            region_box,
            rve_pad,
        )

        # Generate refined mesh in layer thickness
        refinement = app.args.refine_layer
        refine_dict_path = os.path.join(template_dir_abs, "system", "refineMeshDict")
        os.system(
            f"foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir_abs, layer_box)

        # Archive copy of the layer refinement dict
        copy_path = os.path.join(template_dir_abs, "system", "refineLayerMeshDict")
        shutil.copy(refine_dict_path, copy_path)

        # Generate refined mesh in region
        refinement = app.args.refine_region + app.args.refine_layer
        refine_dict_path = os.path.join(template_dir_abs, "system", "refineMeshDict")
        os.system(
            f"foamDictionary -entry castellatedMeshControls/refinementRegions/refinementBox/levels"
            f" -set '( ({refinement} {refinement}) );' {refine_dict_path}"
        )
        openfoam.mesh.refine_RVE(template_dir_abs, region_box)

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

    # Copy template to case dir and then update the case parameters
    shutil.copytree(template_dir_abs, case_dir, dirs_exist_ok=True)
    app.update_beam_spot_size(part, case_dir)
    app.update_material_properties(case_dir)
    app.update_region_start_and_end_times(case_dir, bb_dict, path_name)
    app.update_heatsource_scanfile(case_dir, path_name)
    app.update_exaca_mesh_size(case_dir)

    return


def main():
    """Configure all additivefoam/solidification_region_reduced case directories into
    valid AdditiveFOAM cases
    """
    # Create app instance and update template path
    app = AdditiveFOAM("solidification_region_reduced")

    # Get expected Myna output files
    myna_files = app.settings["data"]["output_paths"][app.step_name]

    # Generate AdditiveFOAM case files for each Myna case
    output_files = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        output_files.append(setup_case(case_dir, app))


if __name__ == "__main__":
    main()
