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
import subprocess
import yaml
import mistlib as mist
import pandas as pd
import numpy as np
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

        self.args, _ = self.parser.parse_known_args()

        super().set_procs()
        super().check_exe(
            "additiveFoam",
        )
        self.update_template_path()

    def update_template_path(self):
        """Updates the template path parameter"""
        print(self.args.template)
        if self.args.template is None:
            template_path = os.path.join(
                os.environ["MYNA_APP_PATH"],
                "additivefoam",
                self.simulation_type,
                "template",
            )
            self.args.template = template_path
        print(self.args.template)

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

    def get_part_resource_template_dir(self, part):
        """Provides the path to the template directory in the myna_resources folder

        Args:
            part: The name of the part
        """
        return os.path.join(
            os.path.dirname(self.input_file),
            "myna_resources",
            part,
            "additivefoam",
            self.simulation_type,
            "template",
        )

    def get_region_resource_template_dir(self, part, region):
        """Provides the path to the template directory in the myna_resources folder

        Args:
            part: The name of the part the region is contained within
            region: The name of the region
        """
        return os.path.join(
            os.path.dirname(self.input_file),
            "myna_resources",
            part,
            region,
            "additivefoam",
            self.simulation_type,
            "template",
        )

    def update_beam_spot_size(self, part, case_dir):
        """Updates the beam spot size in the case directory's constant/heatSourceDict

        Args:
            part: name of part to get spot size from
            case_dir: directory that contains AdditiveFOAM case files to update
        """
        # Extract the spot size (diameter -> radius & mm -> m)
        spot_size = (
            0.5
            * self.settings["data"]["build"]["parts"][part]["spot_size"]["value"]
            * 1e-3
        )

        # Get heatSourceModel
        heat_source_model = (
            subprocess.check_output(
                "foamDictionary -entry beam/heatSourceModel -value "
                + f"{case_dir}/constant/heatSourceDict",
                shell=True,
            )
            .decode("utf-8")
            .strip()
        )

        # 2. Get heatSourceModelCoeffs/dimensions
        heat_source_dimensions = (
            subprocess.check_output(
                f"foamDictionary -entry beam/{heat_source_model}Coeffs/dimensions -value "
                + f"{case_dir}/constant/heatSourceDict",
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
            + f"{case_dir}/constant/heatSourceDict"
        )

    def update_region_start_and_end_times(self, case_dir, bb_dict, scanpath_name):
        """Updates the start and end times of the specified case based on the scan path's
        intersection with the domain

        Args:
            case_dir: case directory to update
            bb_dict: dictionary defining the bounding box of the region
            scanpath_name: name of the scanpath file in the case's `constant` directory
        """
        # Read scan path
        df = pd.read_csv(f"{case_dir}/constant/{scanpath_name}", sep="\s+")

        # Iterate through rows to determine intersection with
        # the region's bounding box
        elapsed_time = 0.0
        start_time = None
        end_time = None
        for index, row in df.iloc[1:].iterrows():
            # If scan path row is a scan vector (Pmod == 1)
            if row["Mode"] == 0:
                v = row["tParam"]
                x1 = row["X(m)"]
                y1 = row["Y(m)"]
                x0 = df.iloc[index - 1]["X(m)"]
                y0 = df.iloc[index - 1]["Y(m)"]
                xs = np.linspace(x0, x1, 1000)
                ys = np.linspace(y0, y1, 1000)
                in_region = any(
                    (xs > bb_dict["bb_min"][0])
                    & (xs < bb_dict["bb_max"][0])
                    & (ys > bb_dict["bb_min"][1])
                    & (ys < bb_dict["bb_max"][1])
                )
                if in_region:
                    end_time = None
                if in_region and (start_time is None):
                    start_time = elapsed_time
                if (not in_region) and (end_time is None):
                    end_time = elapsed_time
                elapsed_time += np.linalg.norm(np.array([x1 - x0, y1 - y0])) / v

            # If scan path row is a spot (Pmod == 0)
            if row["Mode"] == 1:
                elapsed_time += row["tParam"]

        # If all vectors or no vectors are in the region,
        # then set the start and end time
        if start_time is None:
            start_time = 0.0
        if end_time is None:
            end_time = elapsed_time

        start_time = np.round(start_time, 5)
        end_time = np.round(end_time, 5)
        self.update_start_and_end_times(case_dir, start_time, end_time)

    def update_start_and_end_times(self, case_dir, start_time, end_time, n_write=2):
        """Updates the case to adjust the start and end time by adjusting:"

        - start and end times of the simulation in system/controlDict
        - the write interval in system/controlDict (only output at halfway and end)
        - name of initial time-step directory

        Args:
            case_dir: case directory to update
            start_time: start time of the simulation
            end_time: end time of the simulation
            n_write: number of times to write output (must be > 0)
        """
        os.system(
            f"foamDictionary -entry startTime -set {start_time} "
            + f"{case_dir}/system/controlDict"
        )
        os.system(
            f"foamDictionary -entry endTime -set {end_time} "
            + f"{case_dir}/system/controlDict"
        )
        os.system(
            f"foamDictionary -entry writeInterval -set {np.round((1 / n_write) * (end_time - start_time), 8)} "
            + f"{case_dir}/system/controlDict"
        )
        source = os.path.abspath(os.path.join(case_dir, "0"))
        target = os.path.abspath(
            os.path.join(
                case_dir,
                f"{int(start_time) if float(start_time).is_integer() else start_time}",
            )
        )
        if target != source:
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.move(source, target)

    def update_heatsource_scanfile(self, case_dir, scanpath_name):
        """Updates the heatSourceDict to point to the specified scan path file

        Args:
            case_dir: AdditiveFOAM case directory to update
            scanpath_name: name of scanpath file in the case's `constant` directory
        """
        os.system(
            "foamDictionary -entry beam/pathName -set"
            + f""" '"{scanpath_name}"' """
            + f"{case_dir}/constant/heatSourceDict"
        )
