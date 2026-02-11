#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines the shared AdditiveFOAM app functionality for all simulation types"""

import os
import shutil
import subprocess
import yaml
import mistlib as mist
import pandas as pd
import numpy as np
from myna.core.app.base import MynaApp
from myna.application.openfoam.mesh import update_parameter


class AdditiveFOAM(MynaApp):
    """Myna application defining the shared functionality accessible to all
    AdditiveFOAM-based simulation types."""

    def __init__(self):
        super().__init__()
        self.app_type = "additivefoam"

        # Parse app-specific arguments
        self.parse_known_args()
        super().validate_executable(
            "additiveFoam",
        )
        if self.args.exec is None:
            self.args.exec = "additiveFoam"

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
        return bool(all(matches))

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
        update_parameter(
            f"{case_dir}/constant/heatSourceDict",
            f"beam/{absorption_model}Coeffs/eta0",
            absorption,
        )
        update_parameter(
            f"{case_dir}/constant/heatSourceDict",
            f"beam/{absorption_model}Coeffs/etaMin",
            absorption,
        )

        # Update the isotherm in the ExaCA function dictionary if it exists
        exaca_dict = f"{case_dir}/system/ExaCA"
        if os.path.exists(exaca_dict):
            liquidus = mat.get_property("liquidus_temperature", None, None)
            update_parameter(exaca_dict, "ExaCA/isoValue", liquidus)

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
            self.name,
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
        update_parameter(
            f"{case_dir}/constant/heatSourceDict",
            f"beam/{heat_source_model}Coeffs/dimensions",
            heat_source_dim_string,
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
        df = pd.read_csv(f"{case_dir}/constant/{scanpath_name}", sep=r"\s+")

        # Iterate through rows to determine intersection with
        # the region's bounding box
        elapsed_time = 0.0
        time_bounds = [None, None]
        for index, row in df.iloc[1:].iterrows():
            # If scan path row is a scan vector (Pmod == 1)
            if row["Mode"] == 0:
                v = row["tParam"]
                p0 = [df.iloc[index - 1]["X(m)"], df.iloc[index - 1]["Y(m)"]]
                p1 = [row["X(m)"], row["Y(m)"]]
                xs = np.linspace(p0[0], p1[0], 1000)
                ys = np.linspace(p0[1], p1[1], 1000)
                in_region = any(
                    (xs > bb_dict["bb_min"][0])
                    & (xs < bb_dict["bb_max"][0])
                    & (ys > bb_dict["bb_min"][1])
                    & (ys < bb_dict["bb_max"][1])
                )
                if in_region:
                    time_bounds[1] = None
                if in_region and (time_bounds[0] is None):
                    time_bounds[0] = elapsed_time
                if (not in_region) and (time_bounds[1] is None):
                    time_bounds[1] = elapsed_time
                elapsed_time += (
                    np.linalg.norm(np.array([p1[0] - p0[0], p1[1] - p0[1]])) / v
                )

            # If scan path row is a spot (Pmod == 0)
            if row["Mode"] == 1:
                elapsed_time += row["tParam"]

        # If all vectors or no vectors are in the region,
        # then set the start and end time
        if time_bounds[0] is None:
            time_bounds[0] = 0.0
        if time_bounds[1] is None:
            time_bounds[1] = elapsed_time

        time_bounds = np.round(time_bounds, 5)
        self.update_start_and_end_times(case_dir, time_bounds[0], time_bounds[1])

    def update_start_and_end_times(self, case_dir, start_time, end_time):
        """Updates the case to adjust the start and end time by adjusting:"

        - start and end times of the simulation in system/controlDict
        - the write interval in system/controlDict (only output at halfway and end)
        - name of initial time-step directory

        Args:
            case_dir: case directory to update
            start_time: start time of the simulation
            end_time: end time of the simulation
        """
        update_parameter(f"{case_dir}/system/controlDict", "startTime", start_time)
        update_parameter(f"{case_dir}/system/controlDict", "endTime", end_time)
        update_parameter(
            f"{case_dir}/system/controlDict",
            "writeInterval",
            np.round(0.5 * (end_time - start_time), 5),
        )
        source = os.path.abspath(os.path.join(case_dir, "0"))
        target = os.path.abspath(os.path.join(case_dir, f"{start_time}"))
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.move(source, target)

    def update_heatsource_scanfile(self, case_dir, scanpath_name):
        """Updates the heatSourceDict to point to the specified scan path file

        Args:
            case_dir: AdditiveFOAM case directory to update
            scanpath_name: name of scanpath file in the case's `constant` directory
        """
        update_parameter(
            f"{case_dir}/constant/heatSourceDict", "beam/pathName", f'"{scanpath_name}"'
        )

    def update_exaca_mesh_size(self, case_dir):
        """Updates the ExaCA/dx value based on the app settings

        Args:
            case_dir: AdditiveFOAM case directory to update
        """
        update_parameter(f"{case_dir}/system/ExaCA", "ExaCA/dx", self.args.exaca_mesh)

    def update_exaca_region_bounds(self, case_dir, bb):
        """Updates the bounds for the ExaCA output for an AdditiveFOAM case

        Args:
            case_dir: (str) path to case directory
            bb: (np.array, shape (2,3)) bounding box ((xmin, ymin, zmin),(xmax, ymax, zmax))
        """
        update_parameter(
            f"{case_dir}/system/ExaCA",
            "ExaCA/box",
            f"( {bb[0][0]} {bb[0][1]} {bb[0][2]} ) ( {bb[1][0]} {bb[1][1]} {bb[1][2]} )",
        )
