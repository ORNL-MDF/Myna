#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.workflow.load_input import load_input
from myna.application.openfoam import mesh

import argparse
import sys
import os
import shutil
import glob


def create_mesh(case_dir, scale_factor, coarse_res, refinement_level, app=None):

    # Get STL path from myna_data
    case_data = load_input(os.path.join(case_dir, "myna_data.yaml"))
    parts = case_data["build"]["parts"]
    part_key = [x for x in parts.keys()][0]
    stl_path = parts[part_key]["stl"]["file_local"]

    # Preprocess STL and create background mesh
    working_stl_path = mesh.preprocess_stl(case_dir, stl_path, scale_factor)
    bb_dict = mesh.create_stl_cube_mesh(
        case_dir, working_stl_path, [coarse_res, coarse_res, coarse_res], 1e-4
    )

    # Extract STL features and create part mesh
    mesh.extract_stl_features(
        case_dir, working_stl_path, refinement_level, bb_dict["origin"]
    )
    mesh.create_part_mesh(case_dir, working_stl_path, bb_dict, app=app)

    # Convert output to VTK
    result_file = mesh.foam_to_adamantine(case_dir)

    return result_file


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch openfoam/mesh_part_vtk for " + "specified input file"
    )
    parser.add_argument(
        "--scale",
        default=0.001,
        type=float,
        help="Multiple by which to scale the STL file dimensions (default = 0.001, mm -> m)",
    )
    parser.add_argument(
        "--coarse",
        default=320e-6,
        type=float,
        help="Size of coarse mesh in the same units as scaled mesh)",
    )
    parser.add_argument(
        "--refine",
        default=1,
        type=int,
        help="Number of refinement levels for part mesh",
    )

    # Parse command line arguments and get Myna settings
    args = parser.parse_args(argv)
    scale = args.scale
    coarse_res = args.coarse
    refinement_level = args.refine
    settings = load_input(os.environ["MYNA_INPUT"])

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Run AdditiveFOAM case for each Myna case, as needed
    for myna_file, case_dir in zip(
        myna_files, [os.path.dirname(x) for x in myna_files]
    ):
        output_file = create_mesh(case_dir, scale, coarse_res, refinement_level)

        # Move output VTK file to expected Myna location and delete VTK directory
        shutil.move(output_file, myna_file)
        shutil.rmtree(os.path.join(case_dir, "VTK"), ignore_errors=True)

        # Clean .obj files if they were created
        input_dir = os.path.dirname(os.environ["MYNA_INPUT"])
        obj_files = glob.glob(os.path.join(input_dir, "*.obj"))
        for obj_file in obj_files:
            os.remove(obj_file)


if __name__ == "__main__":
    main(sys.argv[1:])
