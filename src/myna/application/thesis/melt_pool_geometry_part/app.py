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
import tempfile
from pathlib import Path
import numpy as np
import polars as pl
from myna.core.metadata import Scanpath
from myna.application.thesis import (
    Thesis,
    Path as ThesisPath,
    adjust_parameter,
    read_parameter,
)


class ThesisMeltPoolGeometryPart(Thesis):
    """3DThesis melt pool geometry simulation at part-layer scale."""

    def __init__(self):
        super().__init__()
        self.class_name = "melt_pool_geometry_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        settings = self._load_case_settings(case_dir, myna_input=myna_input)

        part = list(settings["build"]["parts"].keys())[0]
        layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

        scan_obj = Scanpath(None, part, layer)
        myna_scanfile = scan_obj.file_local
        self._configure_standard_part_case(
            case_dir,
            myna_scanfile,
            settings["build"]["parts"][part]["laser_power"]["value"],
            settings["build"]["parts"][part]["spot_size"]["value"],
            settings["build"]["parts"][part]["spot_size"]["unit"],
            settings,
        )

        index_pairs, df = scan_obj.get_constant_z_slice_indices()

        # For each index pair, create a separate case
        pattern = str(Path(case_dir) / "*.txt")
        configured_case_files = sorted(glob.glob(pattern))
        elapsed_time = 0.0
        total_segments = 0
        for index, pair in enumerate(index_pairs):
            segment_dir = Path(case_dir) / f"path_segment_{index:03}"
            os.makedirs(segment_dir, exist_ok=True)
            for case_file in configured_case_files:
                shutil.copy(case_file, segment_dir / Path(case_file).name)

            segment_scanfile = segment_dir / "Path.txt"
            df_segment = df[0 : pair[1] + 1]
            df_segment.write_csv(segment_scanfile, separator="\t")

            # Write temporary path file for getting elapsed time of the segment to calculate
            # the write times for the melt pool geometry:
            # - Ignore wait times at beginning and end of the scan segment
            # - Distribute `nout` proportionally by segment row count
            # - If last segment, ensure that any missing segments due to int() rounding
            #   are included
            with tempfile.NamedTemporaryFile() as fp:
                df_segment_only = df[pair[0] : pair[1] + 1]
                df_segment_only.write_csv(fp.name, separator="\t")
                thesis_scanpath = ThesisPath()
                thesis_scanpath.loadData(fp.name)
                segment_time, _, segment_time_wait_ini, segment_time_wait_fin = (
                    thesis_scanpath.get_all_scan_stats()
                )
                fraction_segments = (
                    int(self.args.nout * (len(df_segment_only) / len(df)))
                    if len(df) > 0
                    else 0
                )
                total_segments += fraction_segments
                if index == (len(index_pairs) - 1):
                    fraction_segments += self.args.nout - total_segments
                segment_times = np.linspace(
                    elapsed_time + segment_time_wait_ini,
                    elapsed_time + segment_time - segment_time_wait_fin,
                    fraction_segments,
                )
            elapsed_time += segment_time

            mode_file = segment_dir / "Mode.txt"
            adjust_parameter(
                str(mode_file), "Times", ",".join([str(x) for x in segment_times])
            )

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        result_file = os.path.join(self.input_dir, "Data", "snapshot_data.csv")
        existing_results = []
        if check_for_existing_results and os.path.exists(result_file):
            existing_results = [result_file]
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
