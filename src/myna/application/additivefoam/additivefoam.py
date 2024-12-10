#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os, shutil, subprocess
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

    def copy(self, case_dir, mesh_path, mesh_dict):
        use_existing_mesh = False
        # If no template mesh dict exists, write it
        if (not os.path.exists(mesh_path)) or (self.args.overwrite):
            shutil.copytree(self.args.template, case_dir, dirs_exist_ok=True)

            with open(mesh_path, "w") as f:
                yaml.dump(mesh_path, f, default_flow_style=False)

        # If template mesh dict exists, then check if it matches current
        # build, part, and region
        else:
            print(f"Warning: NOT overwriting existing case in: {case_dir}")

            with open(mesh_path, "r") as f:
                existing_dict = yaml.safe_load(f)
            try:
                matches = []
                for key in mesh_dict.keys():
                    entry_match = mesh_dict.get(key) == existing_dict.get(key)
                    matches.append(entry_match)
                if all(matches):
                    use_existing_mesh = True
                else:
                    shutil.copytree(self.args.template, case_dir, dirs_exist_ok=True)
                    with open(mesh_path, "w") as f:
                        yaml.dump(mesh_dict, f, default_flow_style=None)
            except:
                shutil.copytree(self.args.template, case_dir, dirs_exist_ok=True)
                with open(mesh_path, "w") as f:
                    yaml.dump(mesh_dict, f, default_flow_style=None)

        return use_existing_mesh

    def update_material_properties(self, case_dir):
        """Update the material properties for the AdditiveFOAM case based on Mist data

        Args:
            case_dir: path to the case directory to update
        """

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

        # Update the base material laser absorption for the heat source
        absorption = mat.get_property("laser_absorption", None, None)
        absorption_model = (
            subprocess.check_output(
                "foamDictionary -entry beam/absorptionModel -value "
                + f"{case_dir}/constant/heatSourceDict",
                shell=True,
            )
            .decode("utf-8")
            .strip()
        )
        os.system(
            f"foamDictionary -entry beam/{absorption_model}Coeffs/eta0"
            + f' -set "{absorption}" {case_dir}/constant/heatSourceDict'
        )
        os.system(
            f"foamDictionary -entry beam/{absorption_model}Coeffs/etaMin"
            + f' -set "{absorption}" {case_dir}/constant/heatSourceDict'
        )
