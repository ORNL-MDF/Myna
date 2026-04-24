#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import math
import glob
import os
import shutil
import subprocess

import mistlib as mist
import pandas as pd

from myna.application.thesis.parse import adjust_parameter
from myna.core.app.base import MynaApp
from myna.core.utils import working_directory
from myna.core.workflow.load_input import load_input


class Thesis(MynaApp):
    def __init__(
        self,
        input_dir=None,
        input_filename="ParamInput.txt",
        material_filename="Material.txt",
        output_dir=None,
        output_suffix="",
        validate_executable=True,
    ):
        super().__init__()
        self.app_type = "thesis"
        self._validate_thesis_executable = validate_executable

        # Set case directories and input files
        self.input_filename = input_filename
        self.material_filename = material_filename
        if input_dir is not None:
            if output_dir is not None:
                self.set_case(input_dir, output_dir)
            else:
                self.set_case(input_dir, input_dir)
        self.output_suffix = output_suffix

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []

    def _load_case_settings(self, case_dir, myna_input="myna_data.yaml"):
        """Load per-case Myna settings for a configured case directory."""
        return load_input(os.path.join(case_dir, myna_input))

    def _spot_size_scale(self, spot_unit):
        """Convert supported spot-size units to meters."""
        if spot_unit == "mm":
            return 1e-3
        if spot_unit == "um":
            return 1e-6
        return 1

    def _copy_scanfile(self, scanfile, case_dir, filename="Path.txt"):
        """Copy a scanpath file into the case directory."""
        case_scanfile = os.path.join(case_dir, filename)
        shutil.copy(scanfile, case_scanfile)
        return case_scanfile

    def _load_material_information(self, material):
        """Resolve the configured material into a Mist material object."""
        material_dir = os.path.join(
            os.environ["MYNA_INSTALL_PATH"], "mist_material_data"
        )
        mist_path = os.path.join(material_dir, f"{material}.json")
        return mist.core.MaterialInformation(mist_path)

    def _write_case_material(self, case_dir, material):
        """Write the configured material file parameters into a Thesis case's inputs"""
        material_file = os.path.join(case_dir, "Material.txt")
        mist_mat = self._load_material_information(material)
        mist_mat.write_3dthesis_input(material_file)
        return mist_mat

    def _configure_beam_file(
        self, beam_file, power, spot_size, spot_unit, laser_absorption=None
    ):
        """Apply beam parameters shared across Thesis workflows."""
        spot_scale = self._spot_size_scale(spot_unit)
        beam_width = 0.25 * math.sqrt(6) * spot_size * spot_scale

        adjust_parameter(beam_file, "Width_X", beam_width)
        adjust_parameter(beam_file, "Width_Y", beam_width)
        adjust_parameter(beam_file, "Power", power)
        if laser_absorption is not None:
            adjust_parameter(beam_file, "Efficiency", laser_absorption)

    def _configure_case_material_and_domain(self, case_dir, settings):
        """Apply shared material, preheat, and domain settings for a case."""
        material = settings["build"]["build_data"]["material"]["value"]
        mist_mat = self._write_case_material(case_dir, material)

        preheat = settings["build"]["build_data"]["preheat"]["value"]
        adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)
        adjust_parameter(os.path.join(case_dir, "Domain.txt"), "Res", self.args.res)
        return mist_mat

    def _configure_standard_part_case(
        self,
        case_dir,
        scanfile,
        power,
        spot_size,
        spot_unit,
        settings,
        *,
        beam_filename="Beam.txt",
        scan_filename="Path.txt",
        include_beam_efficiency=True,
    ):
        """Populate a standard single-beam Thesis case directory."""
        self.copy_template_to_case(case_dir)
        case_scanfile = self._copy_scanfile(scanfile, case_dir, filename=scan_filename)
        beam_file = os.path.join(case_dir, beam_filename)

        mist_mat = self._configure_case_material_and_domain(case_dir, settings)
        laser_absorption = None
        if include_beam_efficiency:
            laser_absorption = mist_mat.get_property("laser_absorption", None, None)
        self._configure_beam_file(
            beam_file,
            power,
            spot_size,
            spot_unit,
            laser_absorption=laser_absorption,
        )
        return case_scanfile

    def parse_shared_arguments(self):
        self.register_argument(
            "--res",
            default=12.5e-6,
            type=float,
            help="(float) resolution to use for simulations in meters",
        )
        self.register_argument(
            "--nout",
            default=1000,
            type=int,
            help="(int) number of snapshot outputs",
        )

    def parse_configure_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        if self._validate_thesis_executable:
            super().validate_executable("3DThesis")
        if self.args.exec is None:
            self.args.exec = "3DThesis"

    def parse_execute_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        if self._validate_thesis_executable:
            super().validate_executable("3DThesis")
        if self.args.exec is None:
            self.args.exec = "3DThesis"

    def set_case(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, self.input_filename)
        self.material_dir = os.path.join(self.input_dir, self.material_filename)

    def _set_max_threads(self):
        """Write the current processor count into the Thesis settings file."""
        adjust_parameter(
            os.path.join(self.input_dir, "Settings.txt"),
            "MaxThreads",
            self.args.np,
        )

    def _existing_case_results(self, pattern="*.csv"):
        """Return existing Thesis CSV outputs for the current case."""
        return sorted(glob.glob(os.path.join(self.input_dir, "Data", pattern)))

    def _should_skip_case(self, existing_results):
        """Return whether an existing case should be reused."""
        return len(existing_results) > 0 and not self.args.overwrite

    def _run_case_with_optional_result(
        self,
        proc_list,
        result_file=None,
        existing_results=None,
    ):
        """Apply shared execution/skip handling around a Thesis case launch."""
        self._set_max_threads()

        existing_results = [] if existing_results is None else existing_results
        if self._should_skip_case(existing_results):
            print(f"{self.input_dir} has already been simulated. Skipping.")
            if result_file is None:
                return proc_list or []
            return [existing_results[0], proc_list]

        case_directory = os.path.abspath(self.input_dir)
        procs = list(proc_list) if proc_list else []
        procs = self.run_thesis_case(case_directory, procs)
        if result_file is None:
            return procs or []
        return [result_file, procs]

    def _export_single_csv_result(self, filepath, mynafile, column_mapping):
        """Export one Thesis CSV into the Myna schema defined by `column_mapping`."""
        df = pd.read_csv(filepath)
        for source, target in column_mapping.items():
            df[target] = df[source]
        df = df[list(column_mapping.values())]
        df.to_csv(mynafile, index=False)

    def _export_multiple_csv_results(self, filepaths, mynafile, column_mapping):
        """Export multiple decomposed Thesis CSVs into one combined Myna output CSV."""
        df_all = None
        for filepath in filepaths:
            df = pd.read_csv(filepath)
            for source, target in column_mapping.items():
                df[target] = df[source]
            df = df[list(column_mapping.values())]
            if df_all is None:
                df_all = df.copy()
            else:
                df_all = pd.concat([df_all, df])
        if df_all is not None:
            df_all.to_csv(mynafile, index=False)

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
