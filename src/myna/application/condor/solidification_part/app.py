#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Condor behavior for the layer-wise ``solidification_part`` component."""

import os

from myna.application.condor import Condor


class CondorSolidificationPart(Condor):
    """Condor solidification simulation at part-layer scale."""

    def __init__(self, validate_executable=True):
        super().__init__(validate_executable=validate_executable)
        self.class_name = "solidification_part"

    def configure_case(self, case_dir, myna_input="myna_data.yaml"):
        """Populate one Condor case using its Myna case metadata."""
        settings = self._load_case_settings(case_dir, myna_input=myna_input)
        part = next(iter(settings["build"]["parts"]))
        part_settings = settings["build"]["parts"][part]
        layer = next(iter(part_settings["layer_data"]))
        scanfile = part_settings["layer_data"][layer]["scanpath"]["file_local"]
        self._configure_standard_part_case(
            case_dir,
            scanfile,
            part_settings["laser_power"]["value"],
            part_settings["spot_size"]["value"],
            part_settings["spot_size"]["unit"],
            settings,
        )

    def configure(self):
        """Configure every case in the active workflow step."""
        self.parse_configure_arguments()
        for case_dir in self.get_case_dirs():
            self.configure_case(case_dir)

    def execute(self):
        """Run every Condor case and export its solidification fields."""
        self.parse_execute_arguments()
        myna_files = self.get_step_output_paths()

        processes = []
        for case_dir in self.get_case_dirs(output_paths=myna_files):
            self.set_case(case_dir, case_dir)
            processes = self.run_case(processes)

        if self.args.batch:
            self.wait_for_all_process_success(processes)

        for myna_file in myna_files:
            case_dir = os.path.dirname(myna_file)
            self.set_case(case_dir, case_dir)
            self.export_solidification_results(self._existing_case_results(), myna_file)
