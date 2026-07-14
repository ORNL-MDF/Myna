#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Shared behavior for Condor heat-transfer application wrappers."""

import glob
import json
import math
import os
import shutil
import subprocess
from pathlib import Path

import mistlib as mist
import pandas as pd

from myna.core.app import MynaApp
from myna.core.utils import working_directory
from myna.core.workflow.load_input import load_input


class Condor(MynaApp):
    """Base class for configuring and executing Condor cases."""

    def __init__(
        self,
        input_dir=None,
        input_filename="ParamInput.json",
        output_dir=None,
        validate_executable=True,
    ):
        super().__init__()
        self.app_type = "condor"
        self.input_filename = input_filename
        self._validate_condor_executable = validate_executable
        self.case_dir = None
        self.case_input_file = None
        self.output_dir = None
        if input_dir is not None:
            self.set_case(input_dir, output_dir or input_dir)

    @staticmethod
    def _read_json(filename):
        """Read a Condor JSON input file."""
        with open(filename, encoding="utf-8") as stream:
            return json.load(stream)

    @staticmethod
    def _write_json(filename, contents):
        """Write a Condor JSON input file with stable formatting."""
        with open(filename, "w", encoding="utf-8") as stream:
            json.dump(contents, stream, indent=4)
            stream.write("\n")

    def _load_case_settings(self, case_dir, myna_input="myna_data.yaml"):
        """Load the Myna metadata associated with one case."""
        return load_input(os.path.join(case_dir, myna_input))

    @staticmethod
    def _spot_size_scale(spot_unit):
        """Return the conversion factor from a supported spot unit to meters."""
        if spot_unit == "mm":
            return 1e-3
        if spot_unit == "um":
            return 1e-6
        return 1

    @staticmethod
    def _copy_scanfile(scanfile, case_dir, filename="Path.txt"):
        """Copy a Myna/Thesis-format scan path into a Condor case."""
        case_scanfile = os.path.join(case_dir, filename)
        shutil.copy(scanfile, case_scanfile)
        return case_scanfile

    @staticmethod
    def _load_material_information(material):
        """Resolve a configured material into a Mist material object."""
        material_dir = Path(os.environ["MYNA_INSTALL_PATH"]) / "mist_material_data"
        return mist.core.MaterialInformation(material_dir / f"{material}.json")

    def _get_bounds_from_scanpath(self, scanpath, padding=0.5e-3, scale=1e-3):
        """Gets the bounds from a scan path, with padding (in m) if specified. Scale converts scan path dim (mm) to meters"""
        df = pd.read_csv(scanpath, sep=r"\s+")
        pad = padding or 0
        return [
            [scale * df["X(mm)"].min() - pad, scale * df["X(mm)"].max() + pad],
            [scale * df["Y(mm)"].min() - pad, scale * df["Y(mm)"].max() + pad],
            [scale * df["Z(mm)"].min() - pad, scale * df["Z(mm)"].max()],
        ]

    def _write_case_material(self, case_dir, material, preheat):
        """Write Condor material constants using Thesis-compatible assumptions."""
        mist_material = self._load_material_information(material)
        reference_temperature = mist_material.properties[
            "solidus_eutectic_temperature"
        ].value
        constants = {
            "T_0": preheat,
            "T_L": mist_material.get_property(
                "liquidus_temperature", "condor", reference_temperature
            ),
            "k": mist_material.get_property(
                "thermal_conductivity_solid", "condor", reference_temperature
            ),
            "c": mist_material.get_property(
                "specific_heat_solid", "condor", reference_temperature
            ),
            "p": mist_material.get_property("density", "condor", reference_temperature),
        }
        self._write_json(Path(case_dir) / "Material.json", {"constants": constants})
        return mist_material

    def _configure_beam_file(
        self, beam_file, power, spot_size, spot_unit, laser_absorption
    ):
        """Set the Myna-derived beam shape and intensity values."""
        contents = self._read_json(beam_file)
        beam_width = 0.25 * math.sqrt(6) * spot_size * self._spot_size_scale(spot_unit)
        contents["shape"]["width_x"] = beam_width
        contents["shape"]["width_y"] = beam_width
        contents["intensity"]["power"] = power
        contents["intensity"]["efficiency"] = laser_absorption
        self._write_json(beam_file, contents)

    def _configure_domain_file(self, domain_file, scanpath):
        """Set the Condor grid resolution from the configure-stage arguments and bounds from scanpath."""
        contents = self._read_json(domain_file)
        contents.setdefault("domain", {})["resolution"] = self.args.res
        bounds = self._get_bounds_from_scanpath(scanpath)
        contents["domain"]["x"] = bounds[0]
        contents["domain"]["y"] = bounds[1]
        contents["domain"]["z"] = bounds[2]
        self._write_json(domain_file, contents)

    def _configure_standard_part_case(
        self,
        case_dir,
        scanfile,
        power,
        spot_size,
        spot_unit,
        settings,
    ):
        """Create a standard single-beam Condor part case."""
        self.copy_template_to_case(case_dir)
        case_scanfile = self._copy_scanfile(scanfile, case_dir)

        material = settings["build"]["build_data"]["material"]["value"]
        preheat = settings["build"]["build_data"]["preheat"]["value"]
        mist_material = self._write_case_material(case_dir, material, preheat)
        laser_absorption = mist_material.get_property(
            "laser_absorption", "condor", None
        )
        self._configure_beam_file(
            Path(case_dir) / "Beam.json",
            power,
            spot_size,
            spot_unit,
            laser_absorption,
        )
        self._configure_domain_file(Path(case_dir) / "Domain.json", case_scanfile)

    def parse_shared_arguments(self):
        self.register_argument(
            "--res",
            default=12.5e-6,
            type=float,
            help="(float) resolution to use for simulations in meters",
        )

    def _parse_stage_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        if self._validate_condor_executable:
            self.validate_executable("condor")
        if self.args.exec is None:
            self.args.exec = "condor"

    def parse_configure_arguments(self):
        self._parse_stage_arguments()

    def parse_execute_arguments(self):
        self._parse_stage_arguments()

    def set_case(self, input_dir, output_dir):
        """Set paths for one Condor case without replacing workflow context."""
        self.case_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.case_input_file = os.path.join(self.case_dir, self.input_filename)

    def _case_name(self):
        """Return the configured Condor simulation name."""
        return self._read_json(self.case_input_file).get("name", "TestSim")

    def _existing_case_results(self):
        """Return serial or MPI final CSV outputs for the current case."""
        pattern = os.path.join(self.case_dir, "Data", f"{self._case_name()}*_Final.csv")
        return sorted(glob.glob(pattern))

    def run_condor_case(self, case_directory, active_processes):
        """Launch one Condor case and apply serial or batch waiting behavior."""
        with working_directory(case_directory):
            logfile = os.path.join(self.output_dir, "myna_condor_run.log")
            with open(logfile, "w", encoding="utf-8") as stream:
                stream.write("# Myna Condor simulation log\n\n")
                stream.write(f"- Simulation input: {self.case_input_file}\n")
                stream.write(f"- Working directory: {os.getcwd()}\n")
                process = self.start_subprocess_with_mpi_args(
                    [self.args.exec, self.case_input_file],
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                )

            active_processes.append(process)
            if self.args.batch:
                self.wait_for_open_batch_resources(active_processes)
            else:
                self.wait_for_process_success(process)
        return active_processes

    def run_case(self, active_processes):
        """Reuse an existing final output or run the configured Condor case."""
        existing_results = self._existing_case_results()
        if existing_results and not self.args.overwrite:
            print(f"{self.case_dir} has already been simulated. Skipping.")
            return active_processes
        if self.args.overwrite:
            for result in existing_results:
                os.remove(result)
        return self.run_condor_case(os.path.abspath(self.case_dir), active_processes)

    @staticmethod
    def export_solidification_results(filepaths, myna_file):
        """Merge Condor final CSVs and write the Myna ``FileGV`` schema."""
        if not filepaths:
            raise FileNotFoundError(
                f"No Condor final solidification outputs found for {myna_file}."
            )

        required_columns = ["x", "y", "G", "V"]
        frames = []
        for filepath in filepaths:
            frame = pd.read_csv(filepath)
            missing = [column for column in required_columns if column not in frame]
            if missing:
                raise ValueError(
                    f"Condor output '{filepath}' is missing required columns: "
                    f"{', '.join(missing)}"
                )
            frames.append(frame[required_columns])

        output = pd.concat(frames, ignore_index=True)
        output = output.rename(
            columns={
                "x": "x (m)",
                "y": "y (m)",
                "G": "G (K/m)",
                "V": "V (m/s)",
            }
        )
        output.to_csv(myna_file, index=False)
