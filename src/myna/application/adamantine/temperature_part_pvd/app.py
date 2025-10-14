#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Application module for the adamantine/temperature_part_pvd simulation. This app
contains functionality to configure adamantine simulation cases based on Myna metadata
for the corresponding layer within a build. Once cases are configured, cases are
launched sequentially within Docker containers.

The current behavior of the application does not consider the part geometry when meshing
the domain. It is assumed that you do not have knowledge of the geometry of the part
before the current layer, so a "substrate" thickness (specified by the user) is added
below the scan path. The substrate is a rectangular box that spans the bounds of the
scan path for the layer plus the user-specified padding on each side of the scan path.

Material is added based on the scan path location. It is assumed that the user does not
have knowledge of the deposit geometry, so the deposited material size is set to be
the `max(mesh_size_xy, spot size)` in the deposit length and width and
`max(mesh_size_z, layer thickness)` in the deposit height.
"""
import os
import json
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
import numpy as np
import mistlib as mist
from myna.application.adamantine import AdamantineApp


class AdamantineTemperatureApp(AdamantineApp):
    """Simulate the temperature evolution of a part, outputting the results to a VTK
    PVD-format file"""

    def __init__(self, name="temperature_part_pvd"):
        super().__init__(name)
        self.path = str(Path(self.path) / "temperature_part_pvd")

        # Define case file names
        self.case_files = {
            "input": "input.json",
            "scanpath": "scanpath.txt",
            "log": "adamantine.log",
        }

    def parse_mynafile_path_to_dict(self, mynafile):
        """Parses the path of the output Myna file into a dictionary containing the
        build, part, and layer names as strings and the case_dir and mynafile as Path
        objects.
        The path to the Myna file is expected to be in the format:
            `working_dir/build/part/layer/stepname/mynafile`
        """
        dir_parts = Path(mynafile).parent.parts
        case_dict = {
            "build": dir_parts[-4],
            "part": dir_parts[-3],
            "layer": dir_parts[-2],
            "stepname": dir_parts[-1],
            "case_dir": Path(mynafile).parent,
            "mynafile": Path(mynafile),
        }
        case_dict["material"] = self.settings["data"]["build"]["build_data"][
            "material"
        ]["value"]
        case_dict["spot_size"] = (
            self.settings["data"]["build"]["parts"][case_dict["part"]]["spot_size"][
                "value"
            ]
            * 1e-3
        )  # myna spot size in millimeters -> adamantine spot size in meters
        case_dict["laser_power"] = self.settings["data"]["build"]["parts"][
            case_dict["part"]
        ]["laser_power"]["value"]
        case_dict["layer_thickness"] = self.settings["data"]["build"]["build_data"][
            "layer_thickness"
        ]["value"]
        return case_dict

    def parse_configure_arguments(self):
        """Check for arguments relevant to the configure step and update app settings"""
        self.parser.add_argument(
            "--mesh-substrate-depth",
            default=1e-3,
            type=float,
            help="Depth of the substrate to mesh below the scan path, in meters",
        )
        self.parser.add_argument(
            "--mesh-substrate-xy-pad",
            default=0.5e-3,
            type=float,
            help="XY padding of the substrate relative to the scan "
            "path bounds, in meters",
        )
        self.parser.add_argument(
            "--mesh-size-factor",
            default=1,
            type=float,
            help="Multiplicative factor to modify the mesh size. "
            "In x and y, the mesh size is equal to the factor * nominal spot size. "
            "In z, the mesh size is equal to the factor * layer thickness",
        )
        self.parser.add_argument(
            "--write-frequency-factor",
            default=5,
            type=float,
            help="Multiplicative factor to modify the output frequency. "
            "Output frequency is equal to the"
            "(factor * nominal spot size) / median scan speed",
        )
        self.parser.add_argument(
            "--convection-heat-transfer-coef",
            default=100.0,
            type=float,
            help="Heat transfer coefficient for the solid & liquid "
            "convective boundary condition (W m^-2)",
        )
        self.parser.add_argument(
            "--convection-temperature-infty",
            default=300.0,
            type=float,
            help="Temperature at x -> infinity for convective boundary condition (K)",
        )
        self.parser.add_argument(
            "--radiation-temperature-infty",
            default=300.0,
            type=float,
            help="Temperature at x -> infinity for radiative boundary condition (K)",
        )
        self.parser.add_argument(
            "--courant",
            default=0.1,
            type=float,
            help="Courant number for controlling the time step, must be less than 1",
        )
        self.parse_known_args()

    def parse_execute_arguments(self):
        """Check for arguments relevant to the execute step and update app settings"""
        self.parse_known_args()

    def update_material_property_dict_from_mist(self, input_dict: dict, material):
        """Updates the materials dictionary of the adamantine input dictionary
        using the Myna-specified material name and corresponding Mist dictionary"""
        # Write out temporary material properties file, then
        # replace template material dict with Myna's Mist material dict.
        # Assumes that the only material is "material_0" and "n_materials" == 1
        with NamedTemporaryFile("w+b") as tmp_material_input:
            mist_path = (
                Path(os.environ["MYNA_INSTALL_PATH"])
                / Path("mist_material_data")
                / Path(f"{material}.json")
            )
            mist_material = mist.core.MaterialInformation(mist_path)
            mist_material.write_adamantine_input(tmp_material_input.name)
            material_dict = self.boost_info_file_to_dict(tmp_material_input.name)
            input_dict["materials"] = material_dict["materials"]

        # Laser efficiency
        laser_absorption = mist_material.get_property("laser_absorption", None, None)
        input_dict["sources"]["beam_0"]["absorption_efficiency"] = laser_absorption
        return input_dict

    def update_material_boundary_condition_dict(self, input_dict: dict):
        """Update material boundary conditions that are not set by Mist"""
        input_dict["materials"]["material_0"]["solid"][
            "convection_heat_transfer_coef"
        ] = self.args.convection_heat_transfer_coef  # W / (K * m^2)
        input_dict["materials"]["material_0"]["liquid"][
            "convection_heat_transfer_coef"
        ] = self.args.convection_heat_transfer_coef  # W / (K * m^2)
        input_dict["materials"]["material_0"][
            "radiation_temperature_infty"
        ] = self.args.radiation_temperature_infty  # K
        input_dict["materials"]["material_0"][
            "convection_temperature_infty"
        ] = self.args.convection_temperature_infty  # K
        return input_dict

    def update_laser_parameter_dict(self, input_dict: dict, case_dict: dict):
        """Update laser power and spot size in the adamantine input dict from the
        Myna case data.

        Assumes that the only beam is "beam_0" and "n_beams" == 1"""
        input_dict["sources"]["beam_0"]["diameter"] = case_dict["spot_size"]
        input_dict["sources"]["beam_0"]["depth"] = 0.25 * case_dict["spot_size"]
        input_dict["sources"]["beam_0"]["max_power"] = case_dict["laser_power"]
        input_dict["sources"]["beam_0"]["scan_path_file"] = self.case_files["scanpath"]
        input_dict["sources"]["beam_0"]["scan_path_file_format"] = "segment"
        return input_dict

    def configure_case(self, case_dict):
        """Configures the case directory based on available Myna data"""

        # Copy the template to the case directory
        self.copy(case_dict["case_dir"])

        # Load in the input file
        input_path = Path(case_dict["case_dir"]) / Path(self.case_files["input"])
        with open(input_path, "r", encoding="utf-8") as f:
            input_dict = json.load(f)

        # UPDATE MATERIAL PROPERTIES
        input_dict = self.update_material_property_dict_from_mist(
            input_dict, case_dict["material"]
        )
        input_dict = self.update_material_boundary_condition_dict(input_dict)

        # UPDATE BEAM SIZE AND LASER POWER
        input_dict = self.update_laser_parameter_dict(input_dict, case_dict)

        # UPDATE SCAN PATH
        # Convert scan path
        scan_dict = self.convert_myna_local_scanpath_to_adamantine(
            case_dict["part"],
            case_dict["layer"],
            case_dict["case_dir"] / self.case_files["scanpath"],
        )

        # UPDATE DOMAIN GEOMETRY
        # Use the scan path bounds along with the user-specified values
        # - X and Y ranges: scan path bounds + xy_pad on both sides
        # - Z ranges: scan path bounds + substrate depth + 2 * spot_size
        # - Origin is the lower-left corner of the domain
        bounds = np.array(scan_dict["bounds"])
        mesh_sizes = np.array(
            [
                self.args.mesh_size_factor * case_dict["spot_size"],
                self.args.mesh_size_factor * case_dict["spot_size"],
                self.args.mesh_size_factor * case_dict["spot_size"],
            ]
        )
        ranges = np.array(
            [
                (bounds[1, 0] - bounds[0, 0]) + 2 * self.args.mesh_substrate_xy_pad,
                (bounds[1, 1] - bounds[0, 1]) + 2 * self.args.mesh_substrate_xy_pad,
                (
                    (bounds[1, 2] - bounds[0, 2])
                    + self.args.mesh_substrate_depth
                    + 2 * case_dict["spot_size"]
                ),
            ]
        )
        origin = np.array(
            [
                bounds[0, 0] - self.args.mesh_substrate_xy_pad,
                bounds[0, 1] - self.args.mesh_substrate_xy_pad,
                bounds[0, 2] - self.args.mesh_substrate_depth,
            ]
        )
        input_dict["geometry"]["length"] = ranges[0]
        input_dict["geometry"]["width"] = ranges[1]
        input_dict["geometry"]["height"] = ranges[2]
        input_dict["geometry"]["length_origin"] = origin[0]
        input_dict["geometry"]["width_origin"] = origin[1]
        input_dict["geometry"]["height_origin"] = origin[2]
        input_dict["geometry"]["length_divisions"] = int(
            np.rint(ranges[0] / mesh_sizes[0])
        )
        input_dict["geometry"]["width_divisions"] = int(
            np.rint(ranges[1] / mesh_sizes[1])
        )
        input_dict["geometry"]["height_divisions"] = int(
            np.rint(ranges[2] / mesh_sizes[2])
        )
        input_dict["geometry"]["material_height"] = (
            origin[2] + self.args.mesh_substrate_depth
        )

        # UPDATE DEPOSIT BEHAVIOR
        # - Deposited volume is assumed to be on the order of the spot size, or at least
        #   one mesh element
        # - Deposit lead time is a function of the median scan speed in the scan path
        input_dict["geometry"]["deposition_length"] = max(
            mesh_sizes[0], case_dict["spot_size"]
        )
        input_dict["geometry"]["deposition_width"] = max(
            mesh_sizes[0], case_dict["spot_size"]
        )
        input_dict["geometry"]["deposition_height"] = max(
            mesh_sizes[2], case_dict["layer_thickness"]
        )
        input_dict["geometry"]["deposition_lead_time"] = (
            mesh_sizes[0] / scan_dict["scan_speed_median"]
        )

        # UPDATE TIME STEPS
        # - Base update on the max scan speed and the mesh_size
        # - Control the time_step by the courant number which must be
        #   less than 1 for stability
        solid_material = input_dict["materials"]["material_0"]["solid"]
        thermal_diffusivity = np.array(
            [
                solid_material[f"thermal_conductivity_{d}"]
                / (solid_material["density"] * solid_material["specific_heat"])
                for d in ["x", "y", "z"]
            ]
        )
        time_step_courant = np.min(
            self.args.courant * np.power(mesh_sizes, 2) / thermal_diffusivity
        )
        time_step_heuristic = (0.1 * case_dict["spot_size"]) / scan_dict[
            "scan_speed_max"
        ]
        time_step = min(time_step_courant, time_step_heuristic)
        input_dict["time_stepping"]["time_step"] = time_step
        input_dict["time_stepping"]["duration"] = scan_dict["elapsed_time"]

        # UPDATE OUTPUT FREQUENCY
        # - Base output frequency on the spot size
        output_time_frequency = (
            self.args.write_frequency_factor * case_dict["spot_size"]
        ) / scan_dict["scan_speed_median"]
        output_steps = int(np.rint(output_time_frequency / time_step))
        input_dict["post_processor"]["time_steps_between_output"] = output_steps

        # UPDATE OUTPUT NAME
        # - Have output match expected Myna output name base (i.e., without .pvd)
        input_dict["post_processor"]["filename_prefix"] = case_dict[
            "mynafile"
        ].name.replace(".pvd", "")

        # WRITE UPDATED INPUT FILE
        export_file = case_dict["case_dir"] / Path(self.case_files["input"])
        with open(export_file, "w", encoding="utf-8") as ef:
            json.dump(input_dict, ef, indent=4)

    def configure(self):
        """Configure case directories for all cases associated with the Myna step"""
        # Check for arguments relevant to the configure step
        self.parse_configure_arguments()

        # Iterate through cases
        output_files = self.settings["data"]["output_paths"][self.step_name]
        case_dicts = [self.parse_mynafile_path_to_dict(x) for x in output_files]
        for case_dict in case_dicts:
            self.configure_case(case_dict)

    def execute_case(self, case_dict: dict):
        """Execute a case directory using the specified Myna execution parameters"""

        # Run the container with case directory mounted as volume
        # Do not use the Myna mpiexec or mpiflag args, fix MPI options because of
        # running in docker image
        # Open log file for capturing process output
        log_file = case_dict["case_dir"] / self.case_files["log"]
        with open(log_file, "w", encoding="utf-8") as lf:

            # Assemble command and kwargs for launching process
            container_case_path = "/home/myna"
            cmd_args = [
                self.args.exec,
                "-i",
                self.case_files["input"],
                ">",
                self.case_files["log"],
                "2>&1",
            ]
            if self.args.docker_image is not None:
                kwargs = {
                    "remove": True,
                    "volumes": {
                        str(case_dict["case_dir"].expanduser().resolve()): {
                            "bind": container_case_path
                        },
                    },
                    "working_dir": container_case_path,
                }
            else:
                kwargs = {
                    "stdout": lf,
                    "stderr": subprocess.STDOUT,
                }
            process = self.start_subprocess_with_mpi_args(cmd_args, **kwargs)

        return process

    def execute(self):
        """Execute all cases for the Myna step"""
        # Check for arguments relevant to the execute step
        self.parse_execute_arguments()

        # Iterate through cases
        output_files = self.settings["data"]["output_paths"][self.step_name]
        case_dicts = [self.parse_mynafile_path_to_dict(x) for x in output_files]
        processes = []
        for case_dict in case_dicts:
            # Execute the case
            process = self.execute_case(case_dict)

            # Handle serial versus batch submission processes
            if self.args.batch:
                processes.append(process)
                self.wait_for_open_batch_resources(processes)
            else:
                self.wait_for_process_success(process)

        # Wait for all jobs to exit successfully if not finished
        if self.args.batch:
            self.wait_for_all_process_success(processes)
