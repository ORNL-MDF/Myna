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
import shutil
import mistlib as mist
import numpy as np
import pandas as pd
from myna.core.workflow.load_input import load_input
from myna.application.thesis import adjust_parameter, read_parameter, Thesis


class ThesisSolidificationPart(Thesis):
    """3DThesis solidification simulation at part-layer scale."""

    def __init__(self):
        super().__init__(output_suffix=".Solidification")
        self.class_name = "solidification_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        input_path = os.path.join(case_dir, myna_input)
        settings = load_input(input_path)

        part = list(settings["build"]["parts"].keys())[0]
        layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

        self.copy_template_to_case(case_dir)

        myna_scanfile = settings["build"]["parts"][part]["layer_data"][layer][
            "scanpath"
        ]["file_local"]
        case_scanfile = os.path.join(case_dir, "Path.txt")
        shutil.copy(myna_scanfile, case_scanfile)

        beam_file = os.path.join(case_dir, "Beam.txt")
        power = settings["build"]["parts"][part]["laser_power"]["value"]
        spot_size = settings["build"]["parts"][part]["spot_size"]["value"]
        spot_unit = settings["build"]["parts"][part]["spot_size"]["unit"]
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

        material = settings["build"]["build_data"]["material"]["value"]
        material_dir = os.path.join(
            os.environ["MYNA_INSTALL_PATH"], "mist_material_data"
        )
        mist_path = os.path.join(material_dir, f"{material}.json")
        mist_mat = mist.core.MaterialInformation(mist_path)
        mist_mat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))
        laser_absorption = mist_mat.get_property("laser_absorption", None, None)
        adjust_parameter(beam_file, "Efficiency", laser_absorption)

        preheat = settings["build"]["build_data"]["preheat"]["value"]
        adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

        domain_file = os.path.join(case_dir, "Domain.txt")
        adjust_parameter(domain_file, "Res", self.args.res)

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
                return proc_list or []

        case_directory = os.path.abspath(self.input_dir)
        procs = proc_list or []
        procs = self.run_thesis_case(case_directory, procs)
        return procs or []

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
            for i, filepath in enumerate(output_files):
                df = pd.read_csv(filepath)
                df["x (m)"] = df["x"]
                df["y (m)"] = df["y"]
                df["G (K/m)"] = df["G"]
                df["V (m/s)"] = df["V"]
                df = df[["x (m)", "y (m)", "G (K/m)", "V (m/s)"]]
                if i == 0:
                    df_all = df.copy()
                else:
                    df_all = pd.concat([df_all, df])
            df_all.to_csv(mynafile, index=False)
