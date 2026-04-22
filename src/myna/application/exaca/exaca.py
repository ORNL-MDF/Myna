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

from myna.core.app.base import MynaApp
from myna.core.utils import nested_set
from myna.core.workflow.load_input import load_input


class ExaCA(MynaApp):
    def __init__(self):
        super().__init__()
        self.app_type = "exaca"

    def parse_shared_arguments(self):
        """Setup ExaCA-specific inputs"""
        self.register_argument(
            "--cell-size", type=float, help="(float) ExaCA cell size in microns"
        )
        self.register_argument(
            "--nd",
            type=float,
            default=1,
            help="(float) Multiplier for nucleation density, 10^(12) * nd)",
        )
        self.register_argument(
            "--mu",
            type=float,
            default=10,
            help="(float) Critical undercooling mean temperature "
            + "for nucleation, in Kelvin",
        )
        self.register_argument(
            "--std",
            type=float,
            default=2,
            help="(float) Standard deviation for undercooling, in Kelvin",
        )
        self.register_argument(
            "--sub-size",
            type=float,
            default=12.5,
            help="(float) Grain size of substrate, in microns",
        )

    def parse_configure_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self.validate_executable("ExaCA")
        if self.args.exec is None:
            self.args.exec = "ExaCA"

    def parse_execute_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()
        self.validate_executable("ExaCA")
        if self.args.exec is None:
            self.args.exec = "ExaCA"

    def parse_postprocess_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()

    def _get_material_file(self, myna_settings):
        """Resolve the ExaCA material definition file for the current build."""
        material = myna_settings["build"]["build_data"]["material"]["value"]
        return os.path.join(
            os.environ["MYNA_APP_PATH"], "exaca", "materials", f"{material}.json"
        )

    def _get_orientation_file(self):
        """Resolve the grain orientation reference file from the ExaCA install."""
        exaca_exec = shutil.which(self.args.exec)
        if exaca_exec is None:
            raise FileNotFoundError(
                f'{self.name} app executable "{self.args.exec}" was not found.'
            )
        exaca_install_dir = os.path.dirname(os.path.dirname(exaca_exec))
        return os.path.join(
            exaca_install_dir, "share", "ExaCA", "GrainOrientationVectors.csv"
        )

    def _update_input_settings(
        self, input_settings, solid_files, layer_thickness, myna_settings
    ):
        """Apply shared ExaCA input settings for a configured case."""
        input_settings["MaterialFileName"] = self._get_material_file(myna_settings)
        input_settings["GrainOrientationFile"] = self._get_orientation_file()
        nested_set(input_settings, ["Domain", "CellSize"], self.args.cell_size)
        cells_per_layer = np.ceil(layer_thickness / self.args.cell_size)
        nested_set(input_settings, ["Domain", "LayerOffset"], cells_per_layer)
        nested_set(input_settings, ["Domain", "NumberOfLayers"], len(solid_files))
        nested_set(input_settings, ["TemperatureData", "TemperatureFiles"], solid_files)
        nested_set(input_settings, ["Nucleation", "Density"], self.args.nd)
        nested_set(input_settings, ["Nucleation", "MeanUndercooling"], self.args.mu)
        nested_set(input_settings, ["Nucleation", "StDev"], self.args.std)
        nested_set(input_settings, ["Substrate", "MeanSize"], self.args.sub_size)
        return input_settings

    def _replace_run_script_placeholders(self, run_script, replacements):
        """Replace template placeholders in a case run script."""
        with open(run_script, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            for placeholder, value in replacements.items():
                line = line.replace(placeholder, value)
            lines[i] = line
        with open(run_script, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def _patch_case_executable(self, case_dir):
        """Write the resolved ExaCA executable location into a case script."""
        run_script = os.path.join(case_dir, "runCase.sh")
        exaca_exec = shutil.which(self.args.exec)
        if exaca_exec is None:
            raise FileNotFoundError(
                f'{self.name} app executable "{self.args.exec}" was not found.'
            )
        self._replace_run_script_placeholders(
            run_script,
            {
                "{{EXACA_BIN_PATH}}": os.path.dirname(exaca_exec),
                "{{EXACA_EXEC}}": os.path.basename(exaca_exec),
            },
        )

    def _patch_case_ranks(self, case_dir):
        """Write the configured MPI rank count into a case script."""
        self._replace_run_script_placeholders(
            os.path.join(case_dir, "runCase.sh"),
            {"{{RANKS}}": f"{self.args.np}"},
        )

    def setup_exaca_case(self, case_dir, solid_files, layer_thickness):
        """Copy a template and populate shared ExaCA inputs for a case directory."""
        self.copy_template_to_case(case_dir)

        myna_settings = load_input(os.path.join(case_dir, "myna_data.yaml"))
        input_file = os.path.join(case_dir, "inputs.json")
        with open(input_file, "r", encoding="utf-8") as f:
            input_settings = json.load(f)

        input_settings = self._update_input_settings(
            input_settings, solid_files, layer_thickness, myna_settings
        )
        with open(input_file, "w", encoding="utf-8") as f:
            json.dump(input_settings, f, indent=2)

        self._patch_case_executable(case_dir)
        return input_settings
