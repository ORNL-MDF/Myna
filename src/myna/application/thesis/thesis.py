#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import subprocess
from myna.core.app.base import MynaApp
from myna.core.utils import working_directory


class Thesis(MynaApp):
    def __init__(
        self,
        app_type="thesis",
        class_name=None,
        input_dir=None,
        input_filename="ParamInput.txt",
        material_filename="Material.txt",
        output_dir=None,
        output_suffix="",
        validate_executable=True,
    ):
        super().__init__(app_type, class_name)
        self.simulation_type = app_type if class_name is None else class_name

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
        if input_dir is not None:
            if output_dir is not None:
                self.set_case(input_dir, output_dir)
            else:
                self.set_case(input_dir, input_dir)
        self.output_suffix = output_suffix

        # Validate executable
        if validate_executable:
            super().validate_executable("3DThesis")

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []

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
            logfile = os.path.join(self.output_dir, "myna_thesis_run.log")
            with open(logfile, "w", encoding="utf-8") as f:
                f.write("# Myna 3DThesis simulation log\n\n")
                f.write(f"- Simulation input directory: {self.input_dir}\n")
                f.write(f"- Working directory: {os.getcwd()}\n")

                # Execute the case
                cmd_args = [self.args.exec, self.input_file]
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
