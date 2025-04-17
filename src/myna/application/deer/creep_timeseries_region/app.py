#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines the class that defines the application behavior for the
`deer/creep_timeseries_region` application
"""

import os
import shutil
import subprocess
import numpy as np
from myna.application.deer import DeerApp, get_mesh_dimensions, get_mesh_max_block_num
from myna.core.utils import working_directory


class CreepTimeseriesRegionDeerApp(DeerApp):
    """`MynaApp` class to run a Deer creep simulation by taking in an Exodus mesh file
    with Euler Angle variables. Outputs an Exodus file for visualization (not used by
    Myna) and a CSV file with the time series data (used for Myna).

    > ![warning]
    >
    > There is not currently a material database associated with this application, so
    > material-specific behavior will not automatically be resolved. To run this
    > application with different material behavior than the default SS316H simplified
    > behavior, use the `--template` option in the configure dictionary of Myna input
    > file and point to the modified template. Note that file names must be the same
    > for this app to work:
    >
    > - "case.i"
    > - "grain_boundary_properties.i"
    > - "material_model.xml"
    """

    def __init__(
        self,
        sim_type="creep_timeseries_region",
    ):
        super().__init__(sim_type)
        self.parser.add_argument(
            "--loaddir",
            default="z",
            type=str,
            help='(str) loading direction ("x" , "y", "z")',
        )
        self.parser.add_argument(
            "--load",
            default="100",
            type=float,
            help="(float) load in Newtons",
        )
        self.args, _ = self.parser.parse_known_args()
        super().set_procs()
        self.update_template_path()

        # Check that all needed executables are accessible.
        self.validate_executable(default="deer-opt")

        # Set names for template files
        self.orientation_file_name = "orientation.txt"
        self.grain_boundary_file_name = "grain_boundary_properties.i"
        self.case_input_file_name = "case.i"
        self.material_model_file_name = "material_model.xml"
        self.output_csv_name = "wCreep_out.csv"

    def configure_case(self, case_dir, exodus_file):
        """Configure a single case

        Args:
            case_dir: directory to configure into a valid Deer case
            exodus_file: Exodus mesh file associated with the case"""
        self.copy_template_to_dir(case_dir)
        self.generate_orientation_file(case_dir, exodus_file)
        self.update_case_loading_direction(case_dir)

    def configure_all_cases(self):
        """Configure all cases for the Myna step"""
        exodus_files = self.settings["data"]["output_paths"][self.last_step_name]
        output_files = self.settings["data"]["output_paths"][self.step_name]
        case_dirs = [os.path.dirname(x) for x in output_files]
        for case_dir, exodus_file in zip(case_dirs, exodus_files):
            self.configure_case(case_dir, exodus_file)

    def run_case(self, exodus_mesh_file, case_dir):
        """Run a case based on the given input and output file paths

        Args:
            exodus_mesh_file: Exodus mesh file to use as Deer input
            case_dir: directory containing a valid Deer case to run
        """

        # Get mesh properties
        mesh_dims = get_mesh_dimensions(exodus_mesh_file)
        num_blocks = get_mesh_max_block_num(exodus_mesh_file)
        if self.args.loaddir.lower() == "x":
            rve_length = mesh_dims[0]
        elif self.args.loaddir.lower() == "y":
            rve_length = mesh_dims[1]
        elif self.args.loaddir.lower() == "z":
            rve_length = mesh_dims[2]
        else:
            raise ValueError('loaddir must be "x", "y", or "z"')

        # Launch process
        with working_directory(case_dir):
            with open("deer_run.log", "w", encoding="utf-8") as f:
                cmd_args = [
                    self.args.exec,
                    "-i",
                    f"{os.path.join(case_dir, self.grain_boundary_file_name)}",
                    f"{os.path.join(case_dir, self.case_input_file_name)}",
                    f"Mesh/base/file={exodus_mesh_file}",
                    "UserObjects/euler_angle_file/prop_file_name"
                    + f"={os.path.join(case_dir, self.orientation_file_name)}",
                    "UserObjects/euler_angle_file/read_type=block",
                    f"UserObjects/euler_angle_file/nblock={num_blocks}",
                    "Materials/stress/database"
                    + f"={os.path.join(case_dir, self.material_model_file_name)}",
                    f"load={self.args.load}",
                    f"RVE_length={rve_length}",
                ]
                process = self.start_subprocess_with_MPI_args(
                    cmd_args,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )
        return process

    def run_all_cases(self):
        """Run all cases for the Myna step"""
        exodus_files = self.settings["data"]["output_paths"][self.last_step_name]
        csv_files = self.settings["data"]["output_paths"][self.step_name]
        processes = []
        for exodus_file, csv_file in zip(exodus_files, csv_files):
            if (not os.path.exists(csv_file)) or (self.args.overwrite):
                # Execute the case
                process = self.run_case(exodus_file, os.path.dirname(csv_file))

                # Handle serial versus batch submission processes
                if self.args.batch:
                    processes.append(process)
                else:
                    returncode = process.wait()
                    if returncode != 0:
                        error_msg = (
                            f"Subprocess exited with return code {returncode}."
                            + " Check case log files for details."
                        )
                        raise subprocess.SubprocessError(error_msg)

        # Wait for batched jobs to finish
        if self.args.batch:
            for process in processes:
                returncode = process.wait()
                if returncode != 0:
                    error_msg = (
                        f"Subprocess exited with return code {returncode}. "
                        + "Check case log files for details."
                    )
                    raise subprocess.SubprocessError(error_msg)

        # Copy output to the Myna format
        for myna_file in csv_files:
            case_dir = os.path.dirname(myna_file)
            case_file = os.path.join(case_dir, self.output_csv_name)
            shutil.copy(case_file, myna_file)

    def generate_orientation_file(self, case_dir, exodus_mesh_file):
        """Generates the orientation file for an Exodus file with stored Euler angle
        variables: "euler_bunge_zxz_phi1", "euler_bunge_zxz_Phi", and "euler_bunge_zxz_phi2"

        Args:
            case_dir: path to case directory to generate the orientation file for
            exodus_mesh_file: path to the mesh file to get orientations from
        """
        try:
            from netCDF4 import Dataset
        except ImportError as exc:
            raise ImportError(
                'Myna deer app requires "pip install .[deer]" optional dependencies!'
            ) from exc

        # Get max block number from mesh
        block_num_max = get_mesh_max_block_num(exodus_mesh_file)

        # Get orientation data from Exodus mesh variables
        with Dataset(exodus_mesh_file) as mesh:

            # Get euler angles for each filled block
            num_blocks = mesh.variables["eb_prop1"][:].shape[0]
            euler_angles = np.zeros((num_blocks, 3))
            euler_angles[:, 0] = mesh.variables["euler_bunge_zxz_phi1"][:].data
            euler_angles[:, 1] = mesh.variables["euler_bunge_zxz_Phi"][:].data
            euler_angles[:, 2] = mesh.variables["euler_bunge_zxz_phi2"][:].data

            # Map back to overall blocks (including empty ones)
            overall_block_euler_angles = np.zeros((block_num_max, 3))
            overall_block_euler_angles[mesh.variables["eb_prop1"][:].data - 1, :] = (
                euler_angles
            )

            np.savetxt(
                os.path.join(case_dir, self.orientation_file_name),
                overall_block_euler_angles,
                delimiter=" ",
                fmt="%.6f",
            )

    def update_case_loading_direction(self, case_dir):
        """Update case input file with loading direction

        Args:
            case_dir: path to the case directory to update"""
        deer_case_input_file = os.path.join(case_dir, self.case_input_file_name)
        with open(deer_case_input_file, "r", encoding="utf-8") as f:
            input_file_str = f.read()
        input_file_str = input_file_str.replace("{LOADDIR}", self.args.loaddir)
        with open(deer_case_input_file, "w", encoding="utf-8") as f:
            f.write(input_file_str)
