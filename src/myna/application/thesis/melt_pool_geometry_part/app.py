#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/melt_pool_geometry_part."""

import argparse
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
    remove_block_keyword,
    read_parameter,
    replace_first_nonempty_line,
    set_block_keyword,
)


class ThesisMeltPoolGeometryPart(Thesis):
    """3DThesis melt pool geometry simulation at part-layer scale."""

    supports_part_layer_initial_temperature = True
    MINIMUM_THESIS_VERSION = "4.0.0"
    SNAPSHOT_SAMPLING_MODE = "snapshots"
    XY_GRID_SAMPLING_MODE = "xy-grid"

    def __init__(self):
        super().__init__()
        self.class_name = "melt_pool_geometry_part"

    def default_z_resolution(self):
        """Use an isotropic mesh unless the user overrides Z."""
        return self.args.res

    @classmethod
    def _normalize_sampling_mode(cls, value):
        """Normalize supported user-facing melt-pool sampling mode names."""
        normalized = str(value).strip().lower()
        aliases = {
            "snapshot": cls.SNAPSHOT_SAMPLING_MODE,
            "snapshots": cls.SNAPSHOT_SAMPLING_MODE,
            "time-series": cls.SNAPSHOT_SAMPLING_MODE,
            "timeseries": cls.SNAPSHOT_SAMPLING_MODE,
            "xy-grid": cls.XY_GRID_SAMPLING_MODE,
            "grid": cls.XY_GRID_SAMPLING_MODE,
            "solidification": cls.XY_GRID_SAMPLING_MODE,
            "spatial-grid": cls.XY_GRID_SAMPLING_MODE,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise argparse.ArgumentTypeError(
                "Unsupported melt-pool sampling mode "
                f"{value!r}. Expected one of: snapshots, xy-grid."
            ) from exc

    def _sampling_mode(self):
        """Return the configured melt-pool sampling mode."""
        return getattr(self.args, "sampling_mode", self.SNAPSHOT_SAMPLING_MODE)

    def require_supported_3dthesis_version(self):
        """Require the 3DThesis version needed by this app."""
        return self.require_minimum_3dthesis_version(
            self.MINIMUM_THESIS_VERSION,
            feature_name=self.name,
        )

    def _configure_mode_files(self, case_dir, *, sampling_mode, times=None):
        """Update copied template control files for the selected sampling mode."""
        mode_file = Path(case_dir) / "Mode.txt"
        output_file = Path(case_dir) / "Output.txt"

        if sampling_mode == self.XY_GRID_SAMPLING_MODE:
            replace_first_nonempty_line(mode_file, "Solidification")
            set_block_keyword(mode_file, "Solidification", "Tracking", "Surface")
            set_block_keyword(mode_file, "Solidification", "Timestep", "1e-4")
            remove_block_keyword(mode_file, "Solidification", "Times")

            set_block_keyword(output_file, "Temperature", "T", "0")
            set_block_keyword(output_file, "Solidification", "tSol", "1")
            set_block_keyword(output_file, "Solidification", "MP_Stats", "1")
        else:
            replace_first_nonempty_line(mode_file, "Snapshots")
            times_value = "0" if times is None else ",".join(str(x) for x in times)
            set_block_keyword(mode_file, "Snapshots", "Times", times_value)
            set_block_keyword(mode_file, "Snapshots", "Tracking", "Geometry")
            remove_block_keyword(mode_file, "Snapshots", "Timestep")

            set_block_keyword(output_file, "Temperature", "T", "1")
            set_block_keyword(output_file, "Solidification", "tSol", "0")
            remove_block_keyword(output_file, "Solidification", "MP_Stats")

    def _segment_sampling_mode(self, segment_dir):
        """Infer the configured melt-pool sampling mode from a segment Mode file."""
        mode_file = Path(segment_dir) / "Mode.txt"
        if not mode_file.exists():
            return self._sampling_mode()
        for line in mode_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped:
                if stripped == "Solidification":
                    return self.XY_GRID_SAMPLING_MODE
                break
        return self.SNAPSHOT_SAMPLING_MODE

    def parse_configure_arguments(self):
        self.register_argument(
            "--sampling-mode",
            default=self.SNAPSHOT_SAMPLING_MODE,
            type=self._normalize_sampling_mode,
            help="(str) melt-pool sampling mode: `snapshots` for time-series "
            "tracking or `xy-grid` for solidification outputs at each XY grid "
            "location",
        )
        super().parse_configure_arguments()

    def parse_execute_arguments(self):
        self.register_argument(
            "--sampling-mode",
            default=self.SNAPSHOT_SAMPLING_MODE,
            type=self._normalize_sampling_mode,
            help="(str) melt-pool sampling mode: `snapshots` or `xy-grid`; "
            "execute primarily infers the mode from each configured case",
        )
        super().parse_execute_arguments()

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        settings = self._load_case_settings(case_dir, myna_input=myna_input)
        sampling_mode = self._sampling_mode()

        part, layer = self._get_case_part_and_layer(settings)

        scan_obj = Scanpath(None, part, layer)
        myna_scanfile = scan_obj.file_local
        self._configure_standard_part_layer_case(
            case_dir,
            settings,
            scanfile=myna_scanfile,
            apply_initial_temperature=True,
        )
        self._configure_mode_files(case_dir, sampling_mode=sampling_mode)

        index_pairs, df = scan_obj.get_constant_z_slice_indices()

        # For each index pair, create a separate case
        pattern = str(Path(case_dir) / "*.txt")
        configured_case_files = sorted(glob.glob(pattern))
        elapsed_time = 0.0
        total_segments = 0
        for index, pair in enumerate(index_pairs):
            segment_times = []
            if sampling_mode == self.SNAPSHOT_SAMPLING_MODE:
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
                if len(segment_times) == 0:
                    continue

            segment_dir = Path(case_dir) / f"path_segment_{index:03}"
            os.makedirs(segment_dir, exist_ok=True)
            for case_file in configured_case_files:
                shutil.copy(case_file, segment_dir / Path(case_file).name)

            segment_scanfile = segment_dir / "Path.txt"
            df_segment = df[0 : pair[1] + 1]
            df_segment.write_csv(segment_scanfile, separator="\t")
            self._configure_mode_files(
                segment_dir,
                sampling_mode=sampling_mode,
                times=segment_times,
            )

    def configure(self):
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        sampling_mode = self._segment_sampling_mode(self.input_dir)
        if sampling_mode == self.XY_GRID_SAMPLING_MODE:
            output_name = read_parameter(self.input_file, "Name")[0]
            result_file = os.path.join(
                self.input_dir,
                "Data",
                f"{output_name}.Solidification.Final.csv",
            )
            existing_results = []
            if check_for_existing_results:
                existing_results = self._existing_case_results(
                    f"{output_name}.Solidification.Final*.csv"
                )
        else:
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
        self.require_supported_3dthesis_version()
        myna_files = self.get_step_output_paths()

        segment_case_dirs = []
        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            pattern = str(Path(case_dir) / "path_segment_*")
            segment_dirs = sorted(glob.glob(pattern))
            segment_case_dirs.append(segment_dirs)

            for segment_dir in segment_dirs:
                self.set_case(segment_dir, segment_dir)
                _, proc_list = self.run_case(proc_list)

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

        if segment_case_dirs:
            for mynafile, segment_dirs in zip(myna_files, segment_case_dirs):
                df_all_segments = pl.DataFrame(schema=myna_schema)
                for segment_dir in segment_dirs:
                    sampling_mode = self._segment_sampling_mode(segment_dir)
                    if sampling_mode == self.XY_GRID_SAMPLING_MODE:
                        output_name = read_parameter(
                            os.path.join(segment_dir, "ParamInput.txt"), "Name"
                        )[0]
                        result_pattern = os.path.join(
                            segment_dir,
                            "Data",
                            f"{output_name}.Solidification.Final*.csv",
                        )
                        segment_files = sorted(glob.glob(result_pattern))
                        thesis_to_myna_mapping = {
                            "tSol": "time (s)",
                            "MP_length": "length (m)",
                            "MP_width": "width (m)",
                            "MP_depth": "depth (m)",
                            "x": "x (m)",
                            "y": "y (m)",
                        }
                    else:
                        snapshot_data_file = os.path.join(
                            segment_dir, "Data", "snapshot_data.csv"
                        )
                        segment_files = (
                            [snapshot_data_file]
                            if os.path.exists(snapshot_data_file)
                            else []
                        )
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
                    for segment_file in segment_files:
                        df = pl.read_csv(segment_file, columns=list(thesis_schema))
                        df = df.cast(thesis_schema)
                        df = df.rename(thesis_to_myna_mapping)
                        df = df.select(list(myna_schema))
                        df_all_segments = pl.concat([df_all_segments, df])

                if df_all_segments.shape[0] > 0:
                    df_all_segments = df_all_segments.sort(
                        by=["time (s)", "x (m)", "y (m)"]
                    )
                    df_all_segments.write_csv(mynafile)
