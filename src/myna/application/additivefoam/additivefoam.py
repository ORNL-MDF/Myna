#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os, shutil
import yaml
import mistlib as mist

from myna.core.app.base import MynaApp


class AdditiveFOAM(MynaApp):
    def __init__(
        self,
        sim_type,
    ):
        super().__init__("AdditiveFOAM")
        self.simulation_type = sim_type

        self.parser.add_argument(
            "--rx",
            default=1e-3,
            type=float,
            help="(float) width of region along X-axis, in meters",
        )
        self.parser.add_argument(
            "--ry",
            default=1e-3,
            type=float,
            help="(float) width of region along Y-axis, in meters",
        )
        self.parser.add_argument(
            "--rz",
            default=1e-3,
            type=float,
            help="(float) depth of region along Z-axis, in meters",
        )
        self.parser.add_argument(
            "--pad-xy",
            default=2e-3,
            type=float,
            help="(float) size of single-refinement mesh region around"
            + " the double-refined region in XY, in meters",
        )
        self.parser.add_argument(
            "--pad-z",
            default=1e-3,
            type=float,
            help="(float) size of single-refinement mesh region around"
            + " the double-refined region in Z, in meters",
        )
        self.parser.add_argument(
            "--pad-sub",
            default=1e-3,
            type=float,
            help="(float) size of coarse mesh cubic region below"
            + " the refined regions in Z, in meters",
        )
        self.parser.add_argument(
            "--coarse",
            default=640e-6,
            type=float,
            help="(float) size of fine mesh, in meters",
        )
        self.parser.add_argument(
            "--refine-layer",
            default=5,
            type=int,
            help="(int) number of region mesh refinement"
            + " levels in layer (each level halves coarse mesh)",
        )
        self.parser.add_argument(
            "--refine-region",
            default=1,
            type=int,
            help="(int) additional refinement of region mesh"
            + " level after layer refinement (each level halves coarse mesh)",
        )
        self.parser.add_argument(
            "--scale",
            default=0.001,
            type=float,
            help="Multiple by which to scale the STL file dimensions (default = 0.001, mm -> m)",
        )

        self.args = self.parser.parse_args()

        super().set_procs()
        super().check_exe(
            "additiveFoam",
        )

    def copy_template_to_dir(self, target_dir):
        """Copies the specified template directory to the specified target directory"""
        # Ensure directory structure to target exists
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        if self.args.template is not None:
            shutil.copytree(self.args.template, target_dir, dirs_exist_ok=True)

    def has_matching_template_mesh_dict(self, mesh_path, mesh_dict):
        """Checks if there is a usable mesh dictionary in the case directory

        Args:
            mesh_path: path to the template mesh dictionary
            mesh_dict: dictionary object containing the template mesh dictionary

        Return:
            Boolean: True/False if template mesh dict matches
        """
        if (not os.path.exists(mesh_path)) or (self.args.overwrite):
            return False

        # If template mesh dict exists, then check if it matches current
        # build, part, and region
        with open(mesh_path, "r", encoding="utf-8") as f:
            existing_dict = yaml.safe_load(f)
        matches = []
        for key in mesh_dict.keys():
            entry_match = mesh_dict.get(key) == existing_dict.get(key)
            matches.append(entry_match)
        if all(matches):
            return True
        else:
            return False

    def update_material_properties(self, case_dir):

        material = self.settings["data"]["build"]["build_data"]["material"]["value"]
        material_data = os.path.join(
            os.environ["MYNA_INSTALL_PATH"],
            "mist_material_data",
            f"{material}.json",
        )
        mat = mist.core.MaterialInformation(material_data)
        transport_filepath = os.path.join(case_dir, "constant", "transportProperties")
        thermo_filepath = os.path.join(case_dir, "constant", "thermoPath")
        mat.write_additivefoam_input(
            transport_file=transport_filepath, thermo_file=thermo_filepath
        )
