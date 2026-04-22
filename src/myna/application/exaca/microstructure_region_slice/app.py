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
import numpy as np
import pandas as pd
from myna.core.utils import nested_get
from myna.application.exaca import (
    add_rgb_to_vtk,
    convert_id_to_rotation,
    get_fract_nucleated_grains,
    get_mean_grain_area,
    get_wasserstein_distance_misorientation_z,
    grain_id_reader,
)
from myna.application.exaca.microstructure_region import ExaCAMicrostructureRegion


class ExaCAMicrostructureRegionSlice(ExaCAMicrostructureRegion):
    def __init__(self):
        super().__init__()
        self.class_name = "microstructure_region_slice"

    def _configure_case_analysis(self, case_dir, input_settings):
        """Skip analysis file configuration for slice cases, since this is done within
        `self._finalize_case_output` instead of the template analysis file using ExaCA's
        analysis utility that `ExaCAMicrostructureRegion` uses."""
        return

    def _finalize_case_output(self, filepath, myna_file):
        """Convert the raw ExaCA VTK into slice statistics CSV output."""
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
                "Wasserstein distance (100-Z)": np.ones_like(df["X (m)"].to_numpy())
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
