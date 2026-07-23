#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for thesis/depth_map_part."""

import glob
import os
from pathlib import Path

import polars as pl
from myna.application.thesis import Thesis, read_parameter, update_domain_resolution


class ThesisDepthMapPart(Thesis):
    """3DThesis melt pool depth map simulation at part-layer scale."""

    def __init__(self):
        super().__init__(output_suffix=".Solidification")
        self.class_name = "depth_map_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        """Configure a valid 3DThesis case from per-case Myna data."""
        settings = self._load_case_settings(case_dir, myna_input=myna_input)

        part = list(settings["build"]["parts"].keys())[0]
        layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]
        self._configure_standard_part_case(
            case_dir,
            settings["build"]["parts"][part]["layer_data"][layer]["scanpath"][
                "file_local"
            ],
            settings["build"]["parts"][part]["laser_power"]["value"],
            settings["build"]["parts"][part]["spot_size"]["value"],
            settings["build"]["parts"][part]["spot_size"]["unit"],
            settings,
        )

        # Assumption: For the depth mapping, we want to ensure that the z-direction is well-resolved,
        # regardless of the XY grid size
        update_domain_resolution(
            domain_file=Path(case_dir, "Domain.txt"), direction="Z", value=10e-6
        )

    def configure(self):
        """Configure all simulations associated with the Myna step."""
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def run_case(self, proc_list, check_for_existing_results=True):
        """Run the current 3DThesis case."""
        existing_results = []
        if check_for_existing_results:
            existing_results = self._existing_case_results(
                self._depth_map_result_pattern(self.input_dir)
            )
        return self._run_case_with_optional_result(
            proc_list,
            existing_results=existing_results,
        )

    def execute(self):
        """Execute and postprocess all cases for the Myna step."""
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        proc_list = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            self.set_case(case_dir, case_dir)
            proc_list = self.run_case(proc_list)

        if self.args.batch:
            self.wait_for_all_process_success(proc_list)

        self.write_depth_maps(myna_files)

    def postprocess(self):
        """Postprocess files from the executed 3DThesis cases for the Myna step."""
        self.write_depth_maps(self.get_step_output_paths())

    def write_depth_maps(self, myna_files):
        """Convert 3DThesis final CSV outputs into Myna depth-map CSVs."""
        for mynafile in myna_files:
            case_directory = os.path.dirname(mynafile)
            result_file_pattern = os.path.join(
                case_directory, "Data", self._depth_map_result_pattern(case_directory)
            )
            output_files = sorted(glob.glob(result_file_pattern))
            if len(output_files) == 0:
                print(
                    "Warning: No depth map result files found for "
                    f"{case_directory} with pattern {result_file_pattern}"
                )
                continue
            df_all = pl.DataFrame(
                schema={
                    "x (m)": pl.Float64,
                    "y (m)": pl.Float64,
                    "depth (m)": pl.Float64,
                }
            )
            for i, filepath in enumerate(output_files):
                print(i, ":", filepath)
                df = pl.read_csv(filepath)
                df = df.filter(pl.col("z") == df["z"].max())
                df = df.rename({"x": "x (m)", "y": "y (m)", "depth": "depth (m)"})
                df = df.select(["x (m)", "y (m)", "depth (m)"])
                df = df.cast(df_all.schema)
                df_all = pl.concat([df_all, df])
            df_all.write_csv(mynafile)

    def _depth_map_result_pattern(self, case_directory):
        """Return the 3DThesis glob pattern for depth-map final outputs."""
        case_input_file = os.path.join(case_directory, "ParamInput.txt")
        output_name = read_parameter(case_input_file, "Name")[0]
        return f"{output_name}{self.output_suffix}.Final*.csv"
