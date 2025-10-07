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
import numpy as np
import mistlib as mist
from myna.core.app.base import MynaApp
from myna.core.utils import working_directory
from myna.application.thesis import adjust_parameter


class Thesis(MynaApp):
    def __init__(
        self,
        sim_type,
        input_dir=None,
        input_filename="ParamInput.txt",
        material_filename="Material.txt",
        output_dir=None,
        output_suffix="",
        validate_executable=True,
    ):
        super().__init__("3DThesis")
        self.simulation_type = sim_type

        self.parser.add_argument(
            "--res",
            default=12.5e-6,
            type=float,
            help="(float) resolution to use for simulations in meters",
        )
        self.parser.add_argument(
            "--nout",
            default=1000,
            type=int,
            help="(int) number of snapshot outputs",
        )

        self.parse_known_args()

        # Set case directories and input files
        self.input_filename = input_filename
        self.material_filename = material_filename
        self.input_dir = input_dir
        self.output_dir = output_dir
        if input_dir is not None:
            if output_dir is not None:
                self.set_case(input_dir, output_dir)
            else:
                self.set_case(input_dir, input_dir)
        self.output_suffix = output_suffix

        # Set template
        self.set_template_path("thesis", sim_type)

        # Validate executable
        if validate_executable:
            super().validate_executable("3DThesis")

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []

        # Set case file names
        self.case_files = {
            "beam": "Beam.txt",
            "domain": "Domain.txt",
            "material": "Material.txt",
            "path": "Path.txt",
            "mode": "Mode.txt",
            "output": "Output.txt",
            "param": "ParamInput.txt",
            "settings": "Settings.txt",
        }

    def set_case(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, self.input_filename)
        self.material_dir = os.path.join(self.input_dir, self.material_filename)

    def run_thesis_case(self, case_directory, active_processes):
        """Run a 3DThesis case using the MynaApp class functionality

        Args:
            case_directory: (str) path to case directory to run
            active_processes: (list) list of Popen process objects"""
        with working_directory(case_directory):

            output_dir = case_directory
            if self.output_dir is not None:
                output_dir = self.output_dir
            logfile = os.path.join(output_dir, "myna_thesis_run.log")
            with open(logfile, "w", encoding="utf-8") as f:
                f.write("# Myna 3DThesis simulation log\n\n")
                f.write(f"- Simulation input directory: {self.input_dir}\n")
                f.write(f"- Working directory: {os.getcwd()}\n")

                # Execute the case
                cmd_args = [self.args.exec, self.case_files["param"]]
                process = self.start_subprocess_with_mpi_args(
                    cmd_args,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )

            # Handle serial versus batch submission processes
            active_processes.append(process)
            if self.args.batch:
                self.wait_for_open_batch_resources(active_processes)
            else:
                self.wait_for_process_success(process)

            return active_processes

    def update_case_parameters(
        self, case_directory, part=None, region=None, layer=None
    ):
        """Updates the parameters for the case from information in the
        configured Myna input file"""

        # Get case-specific paths for case files
        case_dict = {
            k: os.path.join(case_directory, f) for k, f in self.case_files.items()
        }

        # UPDATE APP-SPECIFIC PARAMETERS

        # Update domain resolution
        domain_file = os.path.join(case_directory, "Domain.txt")
        adjust_parameter(domain_file, "Res", self.args.res)

        # UPDATE BUILD-SPECIFIC PARAMETERS

        # Set preheat temperature
        preheat = self.settings["data"]["build"]["build_data"]["preheat"]["value"]
        adjust_parameter(os.path.join(case_directory, "Material.txt"), "T_0", preheat)

        # Set material properties
        material = self.settings["data"]["build"]["build_data"]["material"]["value"]
        material_dir = os.path.join(
            os.environ["MYNA_INSTALL_PATH"], "mist_material_data"
        )
        mist_path = os.path.join(material_dir, f"{material}.json")
        mist_material = mist.core.MaterialInformation(mist_path)
        mist_material.write_3dthesis_input(case_dict["material"])
        laser_absorption = mist_material.get_property("laser_absorption", None, None)
        adjust_parameter(case_dict["beam"], "Efficiency", laser_absorption)

        # UPDATE PART-SPECIFIC PARAMETERS
        if part is not None:

            # Set beam data
            # - For setting spot size, assume provided spot size is $D4 \sigma$
            # - 3DThesis spot size is $\sqrt(6) \sigma$
            power = self.settings["data"]["build"]["parts"][part]["laser_power"][
                "value"
            ]
            spot_size = self.settings["data"]["build"]["parts"][part]["spot_size"][
                "value"
            ]
            spot_unit = self.settings["data"]["build"]["parts"][part]["spot_size"][
                "unit"
            ]
            spot_scale = 1
            if spot_unit == "mm":
                spot_scale = 1e-3
            elif spot_unit == "um":
                spot_scale = 1e-6
            adjust_parameter(
                case_dict["beam"], "Width_X", 0.25 * np.sqrt(6) * spot_size * spot_scale
            )
            adjust_parameter(
                case_dict["beam"], "Width_Y", 0.25 * np.sqrt(6) * spot_size * spot_scale
            )
            adjust_parameter(case_dict["beam"], "Power", power)

            # UPDATE REGION-SPECIFIC PARAMETERS
            if region is not None:

                # UPDATE LAYER-SPECIFIC PARAMETERS WITHIN THE REGION
                if layer is not None:
                    # Set up scan path
                    myna_scanfile = self.settings["data"]["build"]["parts"][part][
                        "regions"
                    ][region]["layer_data"][layer]["scanpath"]["file_local"]
                    case_scanfile = os.path.join(case_directory, "Path.txt")
                    shutil.copy(myna_scanfile, case_dict["path"])

            # UPDATE LAYER-SPECIFIC PARAMETERS IF THERE IS NO REGION
            elif layer is not None:

                # Set up scan path
                myna_scanfile = self.settings["data"]["build"]["parts"][part][
                    "layer_data"
                ][layer]["scanpath"]["file_local"]
                case_scanfile = os.path.join(case_directory, "Path.txt")
                shutil.copy(myna_scanfile, case_scanfile)
