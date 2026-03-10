#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/melt_pool_geometry_part."""

import glob
import os
import shutil
from pathlib import Path
import mistlib as mist
import numpy as np
import polars as pl
from myna.core.metadata import Scanpath
from myna.core.workflow.load_input import load_input
from myna.application.thesis import (
    Thesis,
    adjust_parameter,
    get_initial_wait_time,
    get_scan_stats,
    read_parameter,
)


class ThesisMeltPoolGeometryPart(Thesis):
    """3DThesis melt pool geometry simulation at part-layer scale."""

    def __init__(self):
        super().__init__()
        self.class_name = "melt_pool_geometry_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        input_path = os.path.join(case_dir, myna_input)
        settings = load_input(input_path)

        part = list(settings["build"]["parts"].keys())[0]
        layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

        self.copy_template_to_case(case_dir)

        scan_obj = Scanpath(None, part, layer)
        myna_scanfile = scan_obj.file_local
        case_scanfile = os.path.join(case_dir, "Path.txt")
        shutil.copy(myna_scanfile, case_scanfile)

        index_pairs, df = scan_obj.get_constant_z_slice_indices()

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

        initial_wait_time = get_initial_wait_time(case_scanfile)
        elapsed_time, _ = get_scan_stats(case_scanfile)
        times = np.linspace(initial_wait_time, elapsed_time, self.args.nout)

        pattern = str(Path(case_dir) / "*.txt")
        configured_case_files = sorted(glob.glob(pattern))
        elapsed_segment_time = 0.0
        for index, pair in enumerate(index_pairs):
            segment_dir = Path(case_dir) / f"path_segment_{index:03}"
            os.makedirs(segment_dir, exist_ok=True)
            for case_file in configured_case_files:
                shutil.copy(case_file, segment_dir / Path(case_file).name)

            segment_scanfile = segment_dir / "Path.txt"
            df_segment = df[0 : pair[1] + 1]
            df_segment.write_csv(segment_scanfile, separator="\t")

            elapsed_time, _ = get_scan_stats(segment_scanfile)
            if index == len(index_pairs) - 1:
                segment_times = [x for x in times if (x >= elapsed_segment_time)]
            else:
                segment_times = [
                    x for x in times if (x >= elapsed_segment_time) & (x < elapsed_time)
                ]
            elapsed_segment_time = elapsed_time

            mode_file = segment_dir / "Mode.txt"
            adjust_parameter(
                str(mode_file), "Times", ",".join([str(x) for x in segment_times])
            )

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        settings_file = os.path.join(self.input_dir, "Settings.txt")
        adjust_parameter(settings_file, "MaxThreads", self.args.np)

        result_file = os.path.join(self.input_dir, "Data", "snapshot_data.csv")
        if check_for_existing_results:
            if os.path.exists(result_file) and not self.args.overwrite:
                print(f"{self.input_dir} has already been simulated. Skipping.")
                return [result_file, proc_list]

        case_directory = os.path.abspath(self.input_dir)
        procs = proc_list.copy()
        procs = self.run_thesis_case(case_directory, procs)
        return [result_file, procs]

    def execute(self):
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        output_files = []
        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            pattern = str(Path(case_dir) / "path_segment_*")
            segment_dirs = sorted(glob.glob(pattern))

            segment_results = []
            for segment_dir in segment_dirs:
                self.set_case(segment_dir, segment_dir)
                result_file, proc_list = self.run_case(proc_list)
                segment_results.append(result_file)
            output_files.append(segment_results)

        if self.args.batch:
            self.wait_for_all_process_success(proc_list)

        myna_schema = {
            "x (m)": pl.Float64,
            "y (m)": pl.Float64,
            "time (s)": pl.Float64,
            "length (m)": pl.Float64,
            "width (m)": pl.Float64,
            "depth (m)": pl.Float64,
        }

        if output_files:
            for mynafile, segment_files in zip(myna_files, output_files):
                thesis_to_myna_mapping = {
                    "Time (s)": "time (s)",
                    "Length Rotated (m)": "length (m)",
                    "Width Rotated (m)": "width (m)",
                    "Depth (m)": "depth (m)",
                    "Beam X": "x (m)",
                    "Beam Y": "y (m)",
                }
                thesis_schema = {
                    k: myna_schema[v] for k, v in thesis_to_myna_mapping.items()
                }
                df_all_segments = pl.DataFrame(schema=myna_schema)
                for snapshot_data_file in segment_files:
                    mode_file = os.path.join(
                        os.path.dirname(os.path.dirname(snapshot_data_file)), "Mode.txt"
                    )
                    times = [
                        x
                        for x in read_parameter(mode_file, "Times")[0].split(",")
                        if x != ""
                    ]
                    n_times = len(times)
                    if n_times > 0:
                        df = pl.read_csv(
                            snapshot_data_file, columns=list(thesis_schema)
                        )
                        df = df.cast(thesis_schema)
                        df = df.rename(thesis_to_myna_mapping)
                        df = df.select(list(myna_schema))
                        df_all_segments = pl.concat([df_all_segments, df])

                if df_all_segments.shape[0] > 0:
                    df_all_segments = df_all_segments.sort(by=["time (s)"])
                    df_all_segments.write_csv(mynafile)
