#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/temperature_surface_part."""

import glob
import os
import subprocess
import time

import pandas as pd
from docker.models.containers import Container

from myna.application.thesis import (
    Thesis,
    Path as ThesisPath,
    adjust_parameter,
    read_parameter,
)
from myna.core.utils import (
    build_part_layer_records,
    build_part_layer_dependency_index,
    format_part_layer_key,
    load_part_layer_interface_index,
)


class ThesisTemperatureSurfacePart(Thesis):
    """3DThesis single-snapshot temperature simulation at part-layer scale."""

    def __init__(self):
        super().__init__()
        self.class_name = "temperature_surface_part"

    def parse_shared_arguments(self):
        """Register arguments shared by configure and execute stages."""
        self.register_argument(
            "--res",
            default=100.0e-6,
            type=float,
            help="(float) resolution to use for simulations in meters",
        )
        self.register_argument(
            "--wait",
            default=0.0,
            type=float,
            help="(float) wait time after the scan path ends before sampling",
        )

    def parse_execute_arguments(self):
        """Register and parse execute-stage arguments."""
        self.register_argument(
            "--use-prior-layer-average",
            dest="use_prior_layer_average",
            default=False,
            action="store_true",
            help="(flag) initialize each layer from the average of the previous "
            "layer output temperature when available",
        )
        super().parse_execute_arguments()

    def _configure_case_snapshot_time(self, case_scanfile, case_dir):
        """Set the single snapshot time to scan completion plus wait time."""
        thesis_scanpath = ThesisPath()
        thesis_scanpath.loadData(case_scanfile)
        elapsed_time, _ = thesis_scanpath.get_elapsed_path_stats()
        snapshot_time = elapsed_time + self.args.wait
        adjust_parameter(os.path.join(case_dir, "Mode.txt"), "Times", snapshot_time)

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        """Configure one top-surface temperature case directory."""
        settings = self._load_case_settings(case_dir, myna_input=myna_input)
        _, _, case_scanfile = self._configure_standard_part_layer_case(
            case_dir,
            settings,
        )
        self._configure_case_snapshot_time(case_scanfile, case_dir)

    def configure(self):
        """Configure all workflow case directories for this step."""
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def _get_result_file_pattern(self, case_directory=None):
        """Return the glob pattern for the case snapshot output."""
        if case_directory is None:
            case_directory = os.path.abspath(self.input_dir)
        output_name = read_parameter(self.input_file, "Name")[0]
        # Thesis snapshot outputs are indexed, so resolve them by pattern.
        return os.path.join(
            case_directory,
            "Data",
            f"{output_name}{self.output_suffix}.Snapshot.*.csv",
        )

    def _resolve_snapshot_file(self, result_file):
        """Resolve a snapshot glob pattern or direct filepath to one CSV."""
        if os.path.exists(result_file):
            return result_file

        result_files = sorted(glob.glob(result_file))
        if not result_files:
            raise FileNotFoundError(
                f"{self.name}: Could not find snapshot output matching {result_file}"
            )
        return result_files[-1]

    def run_case(self, proc_list, check_for_existing_results=True):
        """Run one configured case or reuse existing snapshot output."""
        result_file_pattern = self._get_result_file_pattern()
        existing_results = []
        if check_for_existing_results:
            existing_results = self._existing_case_results(
                pattern=os.path.basename(result_file_pattern)
            )
        return self._run_case_with_optional_result(
            proc_list,
            result_file=result_file_pattern,
            existing_results=existing_results,
        )

    def _write_myna_output(self, snapshot_file, mynafile):
        """Convert a Thesis snapshot CSV into the Myna output format."""
        self._export_single_csv_result(
            snapshot_file,
            mynafile,
            {
                "x": "x (m)",
                "y": "y (m)",
                "z": "z (m)",
                "T": "T (K)",
            },
        )

    def _write_myna_output_from_pattern(self, result_file_pattern, mynafile):
        """Resolve and convert a case snapshot into the final Myna CSV."""
        snapshot_file = self._resolve_snapshot_file(result_file_pattern)
        self._write_myna_output(snapshot_file, mynafile)

    def _set_initial_temperature(self, case_dir, preheat, previous_output=None):
        """Set `T_0` from the previous layer average or the preheat value."""
        material_file = os.path.join(case_dir, "Material.txt")
        temperature = preheat
        if previous_output is not None and os.path.exists(previous_output):
            try:
                temperature = self._get_average_temperature(previous_output)
            except (KeyError, ValueError, pd.errors.EmptyDataError) as exc:
                print(
                    f"{self.name}: Failed to read previous layer temperature from "
                    f"{previous_output}. Using preheat instead. ({exc})"
                )
        elif previous_output is not None:
            print(
                f"{self.name}: Previous layer output {previous_output} was not found. "
                "Using preheat instead."
            )
        adjust_parameter(material_file, "T_0", temperature)
        return temperature

    def _process_is_running(self, process):
        """Return whether a subprocess or container is still running."""
        if isinstance(process, subprocess.Popen):
            return process.poll() is None
        if isinstance(process, Container):
            process.reload()
            return str(process.status).lower() == "running"
        return False

    def _collect_completed_cases(
        self, active_cases, completed_outputs, block_until_one=False
    ):
        """Harvest finished batch cases and write their Myna outputs."""
        completed_any = False
        while True:
            # Materialize finished outputs here so later layers can consume them.
            completed_case_keys = []
            for case_key, active_case in active_cases.items():
                if not self._process_is_running(active_case["process"]):
                    self.wait_for_process_success(active_case["process"])
                    self._write_myna_output_from_pattern(
                        active_case["result_file_pattern"], active_case["myna_file"]
                    )
                    completed_outputs[case_key] = active_case["myna_file"]
                    completed_case_keys.append(case_key)
                    completed_any = True
            for case_key in completed_case_keys:
                del active_cases[case_key]
            if completed_any or not block_until_one:
                return completed_any
            time.sleep(1)

    def _execute_independent_cases(self, myna_files):
        """Execute cases with the normal independent Thesis scheduling flow."""
        output_patterns = []
        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            self.set_case(case_dir, case_dir)
            result_file_pattern, proc_list = self.run_case(proc_list)
            output_patterns.append(result_file_pattern)

        if self.args.batch:
            self.wait_for_all_process_success(proc_list)

        for result_file_pattern, mynafile in zip(output_patterns, myna_files):
            self._write_myna_output_from_pattern(result_file_pattern, mynafile)

    def _execute_dependent_cases(self, myna_files):
        """Execute cases in layer order when prior-layer averaging is enabled."""
        pending_cases = build_part_layer_records(
            myna_files,
            self._load_case_settings,
            error_prefix=self.name,
        )
        active_cases = {}
        completed_outputs = {}
        proc_list = []

        while pending_cases or active_cases:
            launched_case = False
            for part in list(pending_cases):
                records = pending_cases[part]
                if not records:
                    del pending_cases[part]
                    continue
                if part in active_cases:
                    continue

                record = records.pop(0)
                if not records:
                    del pending_cases[part]

                self.set_case(record["case_dir"], record["case_dir"])
                self._set_initial_temperature(
                    record["case_dir"],
                    record["preheat"],
                    completed_outputs.get(part),
                )

                # Detect whether run_case launched a new async batch process.
                proc_count = len(proc_list)
                result_file_pattern, proc_list = self.run_case(proc_list)
                if self.args.batch and len(proc_list) > proc_count:
                    # Keep at most one active layer per part while the job runs.
                    active_cases[part] = {
                        "process": proc_list[-1],
                        "result_file_pattern": result_file_pattern,
                        "myna_file": record["myna_file"],
                    }
                else:
                    # Serial execution completes inside run_case and can be consumed immediately.
                    self._write_myna_output_from_pattern(
                        result_file_pattern, record["myna_file"]
                    )
                    completed_outputs[part] = record["myna_file"]
                launched_case = True

            if self.args.batch:
                self._collect_completed_cases(
                    active_cases,
                    completed_outputs,
                    # If nothing launched this pass, wait for a running part to finish.
                    block_until_one=bool(active_cases) and not launched_case,
                )

    def _execute_part_interface_dependent_cases(self, myna_files, interface_index=None):
        """Execute cases using optional cross-part previous-layer mappings."""
        records_by_part = build_part_layer_records(
            myna_files,
            self._load_case_settings,
            error_prefix=self.name,
        )
        dependency_index, record_index = build_part_layer_dependency_index(
            records_by_part,
            interface_index=(
                load_part_layer_interface_index(self.settings, error_prefix=self.name)
                if interface_index is None
                else interface_index
            ),
            error_prefix=self.name,
        )
        pending_cases = dict(record_index)
        active_cases = {}
        completed_outputs = {}
        proc_list = []

        while pending_cases or active_cases:
            launched_case = False
            for case_key in list(pending_cases):
                previous_key = dependency_index.get(case_key)
                if previous_key is not None:
                    if previous_key in active_cases:
                        continue
                    previous_output = completed_outputs.get(previous_key)
                    if previous_output is None:
                        continue
                else:
                    previous_output = None

                record = pending_cases.pop(case_key)
                self.set_case(record["case_dir"], record["case_dir"])
                self._set_initial_temperature(
                    record["case_dir"],
                    record["preheat"],
                    previous_output,
                )

                proc_count = len(proc_list)
                result_file_pattern, proc_list = self.run_case(proc_list)
                if self.args.batch and len(proc_list) > proc_count:
                    active_cases[case_key] = {
                        "process": proc_list[-1],
                        "result_file_pattern": result_file_pattern,
                        "myna_file": record["myna_file"],
                    }
                else:
                    self._write_myna_output_from_pattern(
                        result_file_pattern, record["myna_file"]
                    )
                    completed_outputs[case_key] = record["myna_file"]
                launched_case = True

            if pending_cases and not launched_case and not active_cases:
                blocked_cases = ", ".join(
                    (
                        f"{format_part_layer_key(case_key)} -> "
                        f"{format_part_layer_key(dependency_index[case_key])}"
                    )
                    for case_key in pending_cases
                    if dependency_index.get(case_key) is not None
                )
                if blocked_cases == "":
                    blocked_cases = ", ".join(
                        format_part_layer_key(case_key) for case_key in pending_cases
                    )
                raise ValueError(
                    f"{self.name}: Could not resolve serial heat accumulation "
                    f"dependencies for the configured interface mappings. Remaining "
                    f"blocked cases: {blocked_cases}."
                )

            if self.args.batch:
                self._collect_completed_cases(
                    active_cases,
                    completed_outputs,
                    block_until_one=bool(active_cases) and not launched_case,
                )

    def execute(self):
        """Execute the workflow using independent or dependent scheduling."""
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        if self.args.use_prior_layer_average:
            interface_index = load_part_layer_interface_index(
                self.settings,
                error_prefix=self.name,
            )
            if interface_index:
                self._execute_part_interface_dependent_cases(
                    myna_files, interface_index=interface_index
                )
            else:
                self._execute_dependent_cases(myna_files)
        else:
            self._execute_independent_cases(myna_files)
