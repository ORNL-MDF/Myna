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
import re
import shutil
import subprocess

import mistlib as mist
import pandas as pd

from myna.application.thesis.parse import adjust_parameter, read_parameter
from myna.core.app.base import MynaApp
from myna.core.utils import working_directory
from myna.core.workflow.load_input import load_input

_UNSET = object()


class Thesis(MynaApp):
    supports_part_layer_initial_temperature = False

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
        self._prior_temperature_surface_step_name = _UNSET
        self._prior_temperature_surface_output_index = _UNSET
        self._initial_temperature_lookup = _UNSET

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

    def _configure_case_material_and_domain(
        self, case_dir, settings, *, initial_temperature=None
    ):
        """Apply shared material, preheat, and domain settings for a case."""
        material = settings["build"]["build_data"]["material"]["value"]
        mist_mat = self._write_case_material(case_dir, material)

        temperature = settings["build"]["build_data"]["preheat"]["value"]
        if initial_temperature is not None:
            temperature = initial_temperature
        adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", temperature)
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
        initial_temperature=None,
    ):
        """Populate a standard single-beam Thesis case directory."""
        self.copy_template_to_case(case_dir)
        case_scanfile = self._copy_scanfile(scanfile, case_dir, filename=scan_filename)
        beam_file = os.path.join(case_dir, beam_filename)

        mist_mat = self._configure_case_material_and_domain(
            case_dir,
            settings,
            initial_temperature=initial_temperature,
        )
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

    def _configure_standard_part_layer_case(
        self,
        case_dir,
        settings,
        *,
        scanfile=None,
        beam_filename="Beam.txt",
        scan_filename="Path.txt",
        include_beam_efficiency=True,
        apply_initial_temperature=False,
    ):
        """Populate a standard single part/layer Thesis case directory."""
        part, layer, part_settings, layer_settings = self._get_case_part_layer_settings(
            settings
        )
        resolved_scanfile = layer_settings["scanpath"]["file_local"]
        if scanfile is not None:
            resolved_scanfile = scanfile

        initial_temperature = None
        if apply_initial_temperature:
            initial_temperature = self._resolve_part_layer_initial_temperature(settings)

        case_scanfile = self._configure_standard_part_case(
            case_dir,
            resolved_scanfile,
            part_settings["laser_power"]["value"],
            part_settings["spot_size"]["value"],
            part_settings["spot_size"]["unit"],
            settings,
            beam_filename=beam_filename,
            scan_filename=scan_filename,
            include_beam_efficiency=include_beam_efficiency,
            initial_temperature=initial_temperature,
        )
        return part, layer, case_scanfile

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

    def parse_part_layer_initial_temperature_arguments(self):
        """Register configure-stage options for automatic part/layer `T_0` setup."""
        self.register_argument(
            "--initial-temperature-file",
            default=None,
            type=str,
            help='(str) CSV file with columns "layer" and "T_0 (K)" '
            "for manual per-layer initialization temperatures",
        )
        self.register_argument(
            "--no-auto-initial-temperature",
            dest="auto_initial_temperature",
            default=True,
            action="store_false",
            help="(flag) disable automatic `T_0` initialization from prior "
            "`temperature_surface_part` outputs or a manual per-layer CSV",
        )

    def _parse_thesis_stage_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        if self._validate_thesis_executable:
            super().validate_executable("3DThesis")
        if self.args.exec is None:
            self.args.exec = "3DThesis"

    def parse_configure_arguments(self):
        if self.supports_part_layer_initial_temperature:
            self.parse_part_layer_initial_temperature_arguments()
        self._parse_thesis_stage_arguments()

    def parse_execute_arguments(self):
        self._parse_thesis_stage_arguments()

    def set_case(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, self.input_filename)
        self.material_dir = os.path.join(self.input_dir, self.material_filename)

    def _normalize_layer_identifier(self, layer):
        """Normalize a case layer identifier into an integer layer number."""
        if isinstance(layer, int):
            return int(layer)
        if isinstance(layer, float) and layer.is_integer():
            return int(layer)
        layer_str = str(layer)
        try:
            return int(layer_str)
        except ValueError:
            matches = re.findall(r"\d+", layer_str)
            if len(matches) == 1:
                return int(matches[0])
        raise ValueError(
            f"{self.name}: Could not parse a numeric layer identifier from {layer!r}"
        )

    def _get_case_part_layer_settings(self, settings):
        """Return the single configured part/layer payload for a case."""
        try:
            part, part_settings = next(iter(settings["build"]["parts"].items()))
            layer, layer_settings = next(iter(part_settings["layer_data"].items()))
        except StopIteration as exc:
            raise ValueError(
                f"{self.name}: Expected at least one configured part and layer."
            ) from exc
        return part, layer, part_settings, layer_settings

    def _get_case_part_and_layer(self, settings):
        """Return the single part/layer pair configured for a case directory."""
        part, layer, _, _ = self._get_case_part_layer_settings(settings)
        return part, layer

    def _get_case_part_and_layer_index(self, settings):
        """Return the normalized `(part, layer)` key for one case directory."""
        part, layer = self._get_case_part_and_layer(settings)
        return part, self._normalize_layer_identifier(layer)

    def _get_average_temperature(self, output_file):
        """Compute the average temperature from a prior-layer output file."""
        df = pd.read_csv(output_file)
        temperature_column = "T (K)" if "T (K)" in df.columns else "T"
        return float(df[temperature_column].mean())

    def _get_case_initial_temperature(self, case_dir):
        """Read the configured `T_0` value from a Thesis case directory."""
        material_file = os.path.join(case_dir, "Material.txt")
        return float(read_parameter(material_file, "T_0")[0])

    def _find_latest_prior_temperature_surface_step_name(self):
        """Return the nearest earlier `temperature_surface_part` step name."""
        if self._prior_temperature_surface_step_name is not _UNSET:
            return self._prior_temperature_surface_step_name

        step_name = None
        if self.step_number is not None:
            for step in self.settings.get("steps", [])[: self.step_number]:
                candidate_name = next(iter(step))
                if step[candidate_name].get("class") == "temperature_surface_part":
                    step_name = candidate_name

        self._prior_temperature_surface_step_name = step_name
        return step_name

    def _get_prior_temperature_surface_output_index(self):
        """Map prior `temperature_surface_part` outputs by `(part, layer)`."""
        if self._prior_temperature_surface_output_index is not _UNSET:
            return self._prior_temperature_surface_output_index

        step_name = self._find_latest_prior_temperature_surface_step_name()
        if step_name is None:
            self._prior_temperature_surface_output_index = {}
            return self._prior_temperature_surface_output_index

        try:
            output_paths = self.get_step_output_paths(step_name)
        except KeyError as exc:
            print(
                f"{self.name}: Could not find output paths for prior "
                f"`temperature_surface_part` step {step_name}. "
                f"Using remaining `T_0` fallbacks. ({exc})"
            )
            self._prior_temperature_surface_output_index = {}
            return self._prior_temperature_surface_output_index

        output_index = {}
        for output_path in output_paths:
            case_dir = os.path.dirname(output_path)
            try:
                settings = self._load_case_settings(case_dir)
                output_index[self._get_case_part_and_layer_index(settings)] = (
                    output_path
                )
            except (FileNotFoundError, KeyError, ValueError, IndexError) as exc:
                print(
                    f"{self.name}: Failed to map prior `temperature_surface_part` "
                    f"output {output_path} to a part/layer case. Skipping. ({exc})"
                )

        self._prior_temperature_surface_output_index = output_index
        return self._prior_temperature_surface_output_index

    def _load_initial_temperature_lookup(self):
        """Load a manual per-layer `T_0` lookup from CSV when configured."""
        if self._initial_temperature_lookup is not _UNSET:
            return self._initial_temperature_lookup

        initial_temperature_file = getattr(self.args, "initial_temperature_file", None)
        if initial_temperature_file is None:
            self._initial_temperature_lookup = {}
            return self._initial_temperature_lookup

        if not os.path.exists(initial_temperature_file):
            raise FileNotFoundError(
                f"{self.name}: Initial temperature file was not found: "
                f"{initial_temperature_file}"
            )

        try:
            df = pd.read_csv(initial_temperature_file)
        except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            raise ValueError(
                f"{self.name}: Failed to read initial temperature file "
                f"{initial_temperature_file}. ({exc})"
            ) from exc

        required_columns = {"layer", "T_0 (K)"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"{self.name}: Initial temperature file {initial_temperature_file} "
                f'must contain columns "layer" and "T_0 (K)".'
            )

        try:
            layer_values = pd.to_numeric(df["layer"], errors="raise")
            temperature_values = pd.to_numeric(df["T_0 (K)"], errors="raise")
        except ValueError as exc:
            raise ValueError(
                f"{self.name}: Initial temperature file {initial_temperature_file} "
                'must contain numeric values for columns "layer" and "T_0 (K)".'
            ) from exc

        if layer_values.isna().any() or temperature_values.isna().any():
            raise ValueError(
                f"{self.name}: Initial temperature file {initial_temperature_file} "
                "must not contain empty layer or temperature values."
            )
        if ((layer_values % 1) != 0).any():
            raise ValueError(
                f"{self.name}: Initial temperature file {initial_temperature_file} "
                'must contain integer values in the "layer" column.'
            )

        lookup = {}
        for layer, temperature in zip(
            layer_values.astype(int), temperature_values.astype(float)
        ):
            if layer in lookup:
                raise ValueError(
                    f"{self.name}: Initial temperature file {initial_temperature_file} "
                    f"contains duplicate entries for layer {layer}."
                )
            lookup[int(layer)] = float(temperature)

        self._initial_temperature_lookup = lookup
        return self._initial_temperature_lookup

    def _resolve_part_layer_initial_temperature(self, settings):
        """Resolve the configured `T_0` for a part/layer thesis case."""
        preheat = settings["build"]["build_data"]["preheat"]["value"]
        if not getattr(self.args, "auto_initial_temperature", True):
            return preheat

        part, layer = self._get_case_part_and_layer_index(settings)
        previous_output = self._get_prior_temperature_surface_output_index().get(
            (part, layer)
        )
        if previous_output is not None:
            previous_case_dir = os.path.dirname(previous_output)
            if os.path.exists(previous_case_dir):
                try:
                    return self._get_case_initial_temperature(previous_case_dir)
                except (OSError, ValueError, IndexError) as exc:
                    print(
                        f"{self.name}: Failed to read prior "
                        f"`temperature_surface_part` case T_0 from "
                        f"{previous_case_dir}. "
                        f"Using remaining `T_0` fallbacks. ({exc})"
                    )
            else:
                print(
                    f"{self.name}: Prior `temperature_surface_part` case "
                    f"{previous_case_dir} was not found. Using remaining `T_0` "
                    "fallbacks."
                )

        lookup = self._load_initial_temperature_lookup()
        if layer in lookup:
            return lookup[layer]

        return preheat

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
