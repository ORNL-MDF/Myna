#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for openfoam/mesh_part_vtk."""

import glob
import os
import shutil
from myna.core.workflow.load_input import load_input
from myna.application.openfoam import mesh
from myna.core.app.base import MynaApp


class OpenFOAMMeshPartVTK(MynaApp):
    """Create part meshes from STL geometry and export to VTK format."""

    def __init__(self):
        super().__init__()
        self.app_type = "openfoam"
        self.class_name = "mesh_part_vtk"

    def parse_execute_arguments(self):
        """Parse execute-step arguments."""
        self.parser.add_argument(
            "--scale",
            default=0.001,
            type=float,
            help="Multiple by which to scale STL dimensions (default=0.001, mm->m)",
        )
        self.parser.add_argument(
            "--coarse",
            default=320e-6,
            type=float,
            help="Size of coarse mesh in scaled mesh units",
        )
        self.parser.add_argument(
            "--refine",
            default=1,
            type=int,
            help="Number of refinement levels for part mesh",
        )
        self.parse_known_args()

    def configure(self):
        """Configure each case directory by copying the template."""
        for case_dir in self.get_case_dirs():
            self.copy_template_to_case(case_dir)

    def create_mesh(self, case_dir, scale_factor, coarse_res, refinement_level):
        """Create OpenFOAM mesh and export VTK for a case directory."""
        case_data = load_input(os.path.join(case_dir, "myna_data.yaml"))
        parts = case_data["build"]["parts"]
        part_key = [x for x in parts.keys()][0]
        stl_path = parts[part_key]["stl"]["file_local"]

        working_stl_path = mesh.preprocess_stl(case_dir, stl_path, scale_factor)
        bb_dict = mesh.create_stl_cube_mesh(
            case_dir, working_stl_path, [coarse_res, coarse_res, coarse_res], 1e-4
        )
        mesh.extract_stl_features(
            case_dir, working_stl_path, refinement_level, bb_dict["origin"]
        )
        mesh.create_part_mesh(case_dir, working_stl_path, bb_dict, app=self)
        return mesh.foam_to_adamantine(case_dir)

    def execute(self):
        """Execute all case directories and write expected Myna output files."""
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        for myna_file, case_dir in zip(myna_files, self.get_case_dirs(output_paths=myna_files)):
            output_file = self.create_mesh(
                case_dir, self.args.scale, self.args.coarse, self.args.refine
            )

            shutil.move(output_file, myna_file)
            shutil.rmtree(os.path.join(case_dir, "VTK"), ignore_errors=True)

            input_dir = os.path.dirname(self.input_file)
            obj_files = glob.glob(os.path.join(input_dir, "*.obj"))
            for obj_file in obj_files:
                os.remove(obj_file)
