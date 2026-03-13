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
import numpy as np
import pandas as pd
from myna.core.utils import nested_get, nested_set
from myna.core.workflow.load_input import load_input
from myna.application.exaca import (
    ExaCA,
    add_rgb_to_vtk,
    convert_id_to_rotation,
    get_fract_nucleated_grains,
    get_mean_grain_area,
    get_wasserstein_distance_misorientation_z,
    grain_id_reader,
)


class ExaCAMicrostructureRegionSlice(ExaCA):
    def __init__(self):
        super().__init__()
        self.class_name = "microstructure_region_slice"

    def setup_case(self, case_dir, solid_files, layer_thickness):
        """Create a valid ExaCA `microstructure_region_slice` case directory."""
        self.copy_template_to_case(case_dir)

        myna_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
        input_file = os.path.join(case_dir, "inputs.json")
        with open(input_file, "r", encoding="utf-8") as f:
            input_settings = json.load(f)

        material = myna_settings["build"]["build_data"]["material"]["value"]
        material_file = os.path.join(
            os.environ["MYNA_APP_PATH"], "exaca", "materials", f"{material}.json"
        )
        input_settings["MaterialFileName"] = material_file

        exaca_install_dir = os.path.dirname(
            os.path.dirname(shutil.which(self.args.exec))
        )
        orientation_file = os.path.join(
            exaca_install_dir, "share", "ExaCA", "GrainOrientationVectors.csv"
        )
        input_settings["GrainOrientationFile"] = orientation_file

        nested_set(input_settings, ["Domain", "CellSize"], self.args.cell_size)
        cells_per_layer = np.ceil(layer_thickness / self.args.cell_size)
        nested_set(input_settings, ["Domain", "LayerOffset"], cells_per_layer)
        nested_set(input_settings, ["Domain", "NumberOfLayers"], len(solid_files))
        nested_set(input_settings, ["TemperatureData", "TemperatureFiles"], solid_files)
        nested_set(input_settings, ["Nucleation", "Density"], self.args.nd)
        nested_set(input_settings, ["Nucleation", "MeanUndercooling"], self.args.mu)
        nested_set(input_settings, ["Nucleation", "StDev"], self.args.std)
        nested_set(input_settings, ["Substrate", "MeanSize"], self.args.sub_size)

        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(input_settings, f, indent=2)

        run_script = os.path.join(case_dir, "runCase.sh")
        with open(run_script, "r", encoding="utf-8") as f:
            lines = f.readlines()
        bin_path = os.path.dirname(shutil.which(self.args.exec))
        exec_name = os.path.basename(self.args.exec)
        for i, line in enumerate(lines):
            lines[i] = line.replace("{{EXACA_BIN_PATH}}", bin_path)
            lines[i] = lines[i].replace("{{EXACA_EXEC}}", exec_name)
        with open(run_script, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def configure(self):
        """Configure all ExaCA microstructure_region_slice cases."""
        self.parse_configure_arguments()
        myna_files = self.get_step_output_paths()
        myna_solid_files = self.get_step_output_paths(self.last_step_name)
        solid_file_sets = []
        for part in self.settings["data"]["build"]["parts"]:
            part_dict = self.settings["data"]["build"]["parts"][part]
            for region in part_dict["regions"]:
                id_str = os.path.join(part, region)
                solid_file_sets.append(
                    sorted([x for x in myna_solid_files if id_str in x])
                )
        layer_thickness = (
            1e6
            * self.settings["data"]["build"]["build_data"]["layer_thickness"]["value"]
        )
        for case_dir, solid_files in zip(
            self.get_case_dirs(output_paths=myna_files), solid_file_sets
        ):
            self.setup_case(case_dir, solid_files, layer_thickness)

    def run_case(self, case_dir):
        """Launch the `runCase.sh` script for the given case."""
        run_script = os.path.join(case_dir, "runCase.sh")
        with open(run_script, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            lines[i] = line.replace("{{RANKS}}", f"{self.args.np}")
        with open(run_script, "w", encoding="utf-8") as f:
            f.writelines(lines)

        chmod_process = self.start_subprocess(["chmod", "755", run_script])
        self.wait_for_process_success(chmod_process)
        process = self.start_subprocess([run_script])
        result_file = os.path.join(case_dir, "exaca.vtk")
        return result_file, process

    def execute(self):
        """Execute all ExaCA microstructure_region_slice cases."""
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

        for filepath, myna_file, file_is_valid in zip(
            output_files, myna_files, files_are_valid
        ):
            if not file_is_valid and os.path.exists(filepath):
                input_file = os.path.join(os.path.dirname(myna_file), "inputs.json")
                with open(input_file, "r", encoding="utf-8") as f:
                    input_dict = json.load(f)
                ref_file = input_dict["GrainOrientationFile"]

                reader = grain_id_reader(filepath)
                structured_points = reader.GetOutput()
                spacing = structured_points.GetSpacing()

                df = convert_id_to_rotation(reader, ref_file)
                zlist = df["Z (m)"].unique()
                slice_z_loc = 0.5 * (df["Z (m)"].max() + df["Z (m)"].min())
                slice_z_loc = zlist[np.argmin(np.abs(zlist - slice_z_loc))]
                df = df[df["Z (m)"] == slice_z_loc]

                mean_grain_area = get_mean_grain_area(df, spacing[0])
                fraction_nucleated_grains = get_fract_nucleated_grains(df)
                wasserstein_z = get_wasserstein_distance_misorientation_z(df, ref_file)

                df_stats = pd.DataFrame(
                    {
                        "X (m)": df["X (m)"].to_numpy(),
                        "Y (m)": df["Y (m)"].to_numpy(),
                        "Z (m)": df["Z (m)"].to_numpy(),
                        "Mean Grain Area (m^2)": np.ones_like(df["X (m)"].to_numpy())
                        * mean_grain_area,
                        "Nulceated Fraction": np.ones_like(df["X (m)"].to_numpy())
                        * fraction_nucleated_grains,
                        "Wasserstein distance (100-Z)": np.ones_like(
                            df["X (m)"].to_numpy()
                        )
                        * wasserstein_z,
                    }
                )
                df_stats.to_csv(myna_file, index=False)

    def postprocess(self):
        """Export RGB-colored VTKs for the slice cases."""
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

            output_vtk = os.path.join(
                os.path.dirname(myna_file),
                nested_get(input_dict, ["Printing", "PathToOutput"]),
                nested_get(input_dict, ["Printing", "OutputFile"]) + ".vtk",
            )

            export_file = output_vtk.replace(".vtk", "_rgb.vtk")
            add_rgb_to_vtk(output_vtk, export_file, ref_file)
