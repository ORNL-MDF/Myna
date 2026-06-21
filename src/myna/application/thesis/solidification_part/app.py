#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/solidification_part."""

import glob
import os
from myna.application.thesis import read_parameter, Thesis


class ThesisSolidificationPart(Thesis):
    """3DThesis solidification simulation at part-layer scale."""

    supports_part_layer_initial_temperature = True

    def __init__(self):
        super().__init__(output_suffix=".Solidification")
        self.class_name = "solidification_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        settings = self._load_case_settings(case_dir, myna_input=myna_input)
        self._configure_standard_part_layer_case(
            case_dir,
            settings,
            apply_initial_temperature=True,
        )

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        existing_results = []
        if check_for_existing_results:
            existing_results = self._existing_case_results()
        return self._run_case_with_optional_result(
            proc_list,
            existing_results=existing_results,
        )

    def execute(self):
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            self.set_case(case_dir, case_dir)
            proc_list = self.run_case(proc_list)

        if self.args.batch:
            self.wait_for_all_process_success(proc_list)

        for mynafile in myna_files:
            case_directory = os.path.dirname(mynafile)
            self.set_case(case_directory, case_directory)
            output_name = read_parameter(self.input_file, "Name")[0]
            result_file_pattern = os.path.join(
                case_directory, "Data", f"{output_name}{self.output_suffix}.Final*.csv"
            )
            output_files = sorted(glob.glob(result_file_pattern))
            self._export_multiple_csv_results(
                output_files,
                mynafile,
                {
                    "x": "x (m)",
                    "y": "y (m)",
                    "G": "G (K/m)",
                    "V": "V (m/s)",
                },
            )
