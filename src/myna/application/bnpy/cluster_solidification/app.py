#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pandas as pd
from myna.application.bnpy import Bnpy


class BnpyClusterSolidification(Bnpy):
    def __init__(self):
        super().__init__()
        self.class_name = "cluster_solidification"

    def parse_execute_arguments(self):
        self.parser.add_argument(
            "--thermal",
            default=None,
            type=str,
            help='thermal step name, for example: "--thermal 3dthesis"',
        )
        super().parse_execute_arguments()

    def execute(self):
        from .execute import run_clustering, train_voxel_model

        self.parse_execute_arguments()
        train_model = self.args.train_model
        overwrite = self.args.overwrite

        myna_files = self.get_step_output_paths()
        thermal_step_name = self.args.thermal
        if thermal_step_name is None:
            thermal_step_name = self.last_step_name
        thermal_files = self.get_step_output_paths(thermal_step_name)

        if train_model:
            train_voxel_model(
                myna_files, thermal_files, self.sF, self.gamma, os.path.dirname(self.input_file)
            )

        output_files = []
        for case_dir, thermal_file in zip(
            self.get_case_dirs(output_paths=myna_files), thermal_files
        ):
            print("Running clustering for:")
            print(f"- {case_dir=}")
            print(f"- {thermal_file=}")
            output_files.append(
                run_clustering(
                    case_dir,
                    thermal_file,
                    self.sF,
                    self.gamma,
                    overwrite,
                    os.path.dirname(self.input_file),
                )
            )

        for filepath, mynafile in zip(output_files, myna_files):
            df = pd.read_csv(filepath)
            df.to_csv(mynafile, index=False)
