#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import json
import os
import shutil
import polars as pl
from myna.core.utils import nested_get, nested_set
from myna.application.exaca import ExaCA, add_rgb_to_vtk


class ExaCAMicrostructureRegion(ExaCA):
    def __init__(self):
        super().__init__()
        self.class_name = "microstructure_region"

    def setup_case(self, case_dir, solid_files, layer_thickness):
        """Configure a valid ExaCA case directory for the current region."""
        input_settings = self.setup_exaca_case(case_dir, solid_files, layer_thickness)
        self._configure_case_analysis(case_dir, input_settings)

    def _configure_case_analysis(self, case_dir, input_settings):
        """Populate grain-analysis slice bounds for a region case."""
        analysis_file = os.path.join(case_dir, "analysis.json")
        with open(analysis_file, "r", encoding="utf-8") as f:
            analysis_settings = json.load(f)

        df = pl.read_csv(
            nested_get(input_settings, ["TemperatureData", "TemperatureFiles"])[0]
        )
        if df.is_empty():
            return
        xmin, xmax = [df["x"].min(), df["x"].max()]
        ymin, ymax = [df["y"].min(), df["y"].max()]
        spacing = nested_get(input_settings, ["Domain", "CellSize"])
        dx = (xmax - xmin) * 1e6 / spacing
        dy = (ymax - ymin) * 1e6 / spacing
        ind_x_mid = int(0.5 * dx)
        ind_y_mid = int(0.5 * dy)

        dz = nested_get(input_settings, ["Domain", "NumberOfLayers"]) * nested_get(
            input_settings, ["Domain", "LayerOffset"]
        )
        ind_z_mid = int(0.8 * dz)

        nested_set(
            analysis_settings, ["Regions", "XY", "zBounds"], [ind_z_mid, ind_z_mid]
        )
        nested_set(
            analysis_settings, ["Regions", "XZ", "yBounds"], [ind_y_mid, ind_y_mid]
        )
        nested_set(
            analysis_settings, ["Regions", "YZ", "xBounds"], [ind_x_mid, ind_x_mid]
        )

        with open(analysis_file, "w", encoding="utf-8") as f:
            json.dump(analysis_settings, f, indent=2)

    def _get_region_case_setup_data(self):
        """Return region case directories paired with their solidification inputs."""
        myna_files = self.get_step_output_paths()
        myna_solid_files = self.get_step_output_paths(self.last_step_name)
        solid_file_sets = []
        for part, part_dict in self.settings["data"]["build"]["parts"].items():
            for region in part_dict["regions"]:
                id_str = os.path.join(part, region)
                solid_file_sets.append(
                    sorted(
                        [
                            filepath
                            for filepath in myna_solid_files
                            if id_str in filepath
                        ]
                    )
                )

        layer_thickness = (
            1e6
            * self.settings["data"]["build"]["build_data"]["layer_thickness"]["value"]
        )
        return [
            (case_dir, solid_files, layer_thickness)
            for case_dir, solid_files in zip(
                self.get_case_dirs(output_paths=myna_files), solid_file_sets
            )
        ]

    def configure(self):
        """Configure all ExaCA microstructure_region cases."""
        self.parse_configure_arguments()
        for (
            case_dir,
            solid_files,
            layer_thickness,
        ) in self._get_region_case_setup_data():
            self.setup_case(case_dir, solid_files, layer_thickness)

    def run_case(self, case_dir):
        """Launch the `runCase.sh` script for the given case."""
        self._patch_case_ranks(case_dir)
        run_script = os.path.join(case_dir, "runCase.sh")

        chmod_process = self.start_subprocess(["chmod", "755", run_script])
        self.wait_for_process_success(chmod_process)
        process = self.start_subprocess([run_script])
        result_file = os.path.join(case_dir, "exaca.vtk")
        return result_file, process

    def _finalize_case_output(self, filepath, myna_file):
        """Promote the raw ExaCA VTK to the workflow output path."""
        shutil.move(filepath, myna_file)

    def execute(self):
        """Execute all ExaCA microstructure_region cases."""
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()
        _, _, files_are_valid = self.get_output_file_status()

        output_files = []
        processes = []
        for myna_file, case_dir, file_is_valid in zip(
            myna_files, self.get_case_dirs(output_paths=myna_files), files_are_valid
        ):
            if not file_is_valid or self.args.overwrite:
                output_file, proc = self.run_case(case_dir)
                output_files.append(output_file)
                if self.args.batch:
                    processes.append(proc)
                else:
                    self.wait_for_process_success(proc)
            else:
                output_files.append(myna_file)
        if self.args.batch:
            self.wait_for_all_process_success(processes)

        for filepath, mynafile, file_is_valid in zip(
            output_files, myna_files, files_are_valid
        ):
            if not file_is_valid and os.path.exists(filepath):
                self._finalize_case_output(filepath, mynafile)

    def postprocess(self):
        """Export RGB-colored VTKs for valid ExaCA outputs."""
        self.parse_postprocess_arguments()
        myna_files = self.get_step_output_paths()
        _, _, files_are_valid = self.get_output_file_status()

        for myna_file, valid in zip(myna_files, files_are_valid):
            if not valid:
                continue
            input_file = os.path.join(os.path.dirname(myna_file), "inputs.json")
            with open(input_file, "r", encoding="utf-8") as f:
                input_dict = json.load(f)
            ref_file = input_dict["GrainOrientationFile"]

            export_file = myna_file.replace(".vtk", "_rgb.vtk")
            add_rgb_to_vtk(myna_file, export_file, ref_file)
