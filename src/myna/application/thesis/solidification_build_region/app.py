#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/solidification_build_region."""

import os
import shutil
import polars as pl
from myna.application.thesis import (
    read_parameter,
    Thesis,
    Path as ThesisPath,
)


class ThesisSolidificationBuildRegion(Thesis):
    """3DThesis solidification simulation at build-region scale."""

    def __init__(self):
        super().__init__(output_suffix=".Solidification")
        self.class_name = "solidification_build_region"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        settings = self._load_case_settings(case_dir, myna_input=myna_input)

        self.copy_template_to_case(case_dir)
        beam_file_template = os.path.join(case_dir, "Beam.txt")

        build_region = list(settings["build"].get("build_regions").keys())[0]
        build_region_dict = settings["build"]["build_regions"][build_region]
        parts = build_region_dict["partlist"]
        print_order = settings["build"]["build_data"]["print_order"]["value"]
        elapsed_time = 0.0
        beam_index = 1
        for part in print_order:
            if part in parts:
                layer = list(build_region_dict["parts"][part]["layer_data"].keys())[0]
                myna_scanfile = build_region_dict["parts"][part]["layer_data"][layer][
                    "scanpath"
                ]["file_local"]
                case_scanfile = os.path.join(case_dir, f"Path_{beam_index}.txt")
                shutil.copy(myna_scanfile, case_scanfile)

                # Add elapsed time to start of scanpath
                thesis_scanpath = ThesisPath()
                thesis_scanpath.loadData(case_scanfile)
                scan_time, _ = thesis_scanpath.get_elapsed_path_stats()
                df_scan = pl.read_csv(case_scanfile, separator="\t")
                wait_dict = df_scan.row(0, named=True)
                wait_dict["Mode"] = 1
                wait_dict["tParam"] = elapsed_time
                df_wait = pl.DataFrame(wait_dict)
                df_scan = pl.concat([df_wait, df_scan])
                df_scan.write_csv(case_scanfile, separator="\t")
                elapsed_time += scan_time

                beam_file = os.path.join(case_dir, f"Beam_{beam_index}.txt")
                shutil.copy(beam_file_template, beam_file)
                self._configure_beam_file(
                    beam_file,
                    build_region_dict["parts"][part]["laser_power"]["value"],
                    build_region_dict["parts"][part]["spot_size"]["value"],
                    build_region_dict["parts"][part]["spot_size"]["unit"],
                )

                beam_index += 1

        self._configure_case_material_and_domain(case_dir, settings)

        os.remove(beam_file_template)

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        case_directory = os.path.abspath(self.input_dir)
        output_name = read_parameter(self.input_file, "Name")[0]
        result_file = os.path.join(
            case_directory, "Data", f"{output_name}{self.output_suffix}.Final.csv"
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
                    "G": "G (K/m)",
                    "V": "V (m/s)",
                },
            )
