#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/solidification_build_region."""

import glob
import os
import shutil
import mistlib as mist
import numpy as np
import pandas as pd
import polars as pl
from myna.core.workflow.load_input import load_input
from myna.application.thesis import (
    get_scan_stats,
    adjust_parameter,
    read_parameter,
    Thesis,
)


class ThesisSolidificationBuildRegion(Thesis):
    """3DThesis solidification simulation at build-region scale."""

    def __init__(self):
        super().__init__(output_suffix=".Solidification")
        self.class_name = "solidification_build_region"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        input_path = os.path.join(case_dir, myna_input)
        settings = load_input(input_path)

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

                scan_time, _ = get_scan_stats(case_scanfile)
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
                power = build_region_dict["parts"][part]["laser_power"]["value"]
                spot_size = build_region_dict["parts"][part]["spot_size"]["value"]
                spot_unit = build_region_dict["parts"][part]["spot_size"]["unit"]
                spot_scale = 1
                if spot_unit == "mm":
                    spot_scale = 1e-3
                elif spot_unit == "um":
                    spot_scale = 1e-6

                adjust_parameter(
                    beam_file, "Width_X", 0.25 * np.sqrt(6) * spot_size * spot_scale
                )
                adjust_parameter(
                    beam_file, "Width_Y", 0.25 * np.sqrt(6) * spot_size * spot_scale
                )
                adjust_parameter(beam_file, "Power", power)

                beam_index += 1

        material = settings["build"]["build_data"]["material"]["value"]
        material_dir = os.path.join(
            os.environ["MYNA_INSTALL_PATH"], "mist_material_data"
        )
        mist_path = os.path.join(material_dir, f"{material}.json")
        mist_mat = mist.core.MaterialInformation(mist_path)
        mist_mat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))

        preheat = settings["build"]["build_data"]["preheat"]["value"]
        adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

        domain_file = os.path.join(case_dir, "Domain.txt")
        adjust_parameter(domain_file, "Res", self.args.res)

        os.remove(beam_file_template)

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        settings_file = os.path.join(self.input_dir, "Settings.txt")
        adjust_parameter(settings_file, "MaxThreads", self.args.np)

        if check_for_existing_results:
            output_files = glob.glob(os.path.join(self.input_dir, "Data", "*.csv"))
            if (len(output_files) > 0) and not self.args.overwrite:
                print(f"{self.input_dir} has already been simulated. Skipping.")
                result_file = output_files[0]
                return [result_file, proc_list]

        case_directory = os.path.abspath(self.input_dir)
        output_name = read_parameter(self.input_file, "Name")[0]
        result_file = os.path.join(
            case_directory, "Data", f"{output_name}{self.output_suffix}.Final.csv"
        )
        procs = proc_list.copy()
        procs = self.run_thesis_case(case_directory, procs)
        return [result_file, procs]

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
            df = pd.read_csv(filepath)
            df["x (m)"] = df["x"]
            df["y (m)"] = df["y"]
            df["G (K/m)"] = df["G"]
            df["V (m/s)"] = df["V"]
            df = df[["x (m)", "y (m)", "G (K/m)", "V (m/s)"]]
            df.to_csv(mynafile, index=False)
