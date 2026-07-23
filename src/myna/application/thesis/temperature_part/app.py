#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/temperature_part."""

import os
import numpy as np
from myna.application.thesis import (
    adjust_parameter,
    read_parameter,
    Thesis,
    Path as ThesisPath,
)


class ThesisTemperaturePart(Thesis):
    """3DThesis temperature simulation at part-layer scale."""

    supports_part_layer_initial_temperature = True

    def __init__(self):
        super().__init__()
        self.class_name = "temperature_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        settings = self._load_case_settings(case_dir, myna_input=myna_input)
        _, _, case_scanfile = self._configure_standard_part_layer_case(
            case_dir,
            settings,
            apply_initial_temperature=True,
        )

        mode_file = os.path.join(case_dir, "Mode.txt")
        thesis_scanpath = ThesisPath()
        thesis_scanpath.loadData(case_scanfile)
        elapsed_time, _ = thesis_scanpath.get_elapsed_path_stats()
        times = np.linspace(0, elapsed_time, self.args.nout)
        adjust_parameter(mode_file, "Times", ",".join([str(x) for x in times]))

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        case_directory = os.path.abspath(self.input_dir)
        output_name = read_parameter(self.input_file, "Name")[0]
        result_file = os.path.join(
            case_directory,
            "Data",
            f"{output_name}{self.output_suffix}.Snapshot.{self.args.nout - 1}.csv",
        )
        existing_results = []
        if check_for_existing_results:
            existing_results = self._existing_case_results()
        return self._run_case_with_optional_result(
            proc_list,
            result_file=result_file,
            existing_results=existing_results,
        )

    def execute(self):
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        output_files = []
        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            self.set_case(case_dir, case_dir)
            result_file, proc_list = self.run_case(proc_list)
            output_files.append(result_file)

        if self.args.batch:
            self.wait_for_all_process_success(proc_list)

        for filepath, mynafile in zip(output_files, myna_files):
            self._export_single_csv_result(
                filepath,
                mynafile,
                {
                    "x": "x (m)",
                    "y": "y (m)",
                    "z": "z (m)",
                    "T": "T (K)",
                },
            )
