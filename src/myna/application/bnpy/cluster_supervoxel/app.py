#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import glob
import os
from myna.application.bnpy import Bnpy


class BnpyClusterSupervoxel(Bnpy):
    def __init__(self):
        super().__init__()
        self.class_name = "cluster_supervoxel"

    def parse_execute_arguments(self):
        self.parser.add_argument(
            "--cluster",
            default="",
            type=str,
            help="input cluster step name, for example: --cluster cluster",
        )
        self.parser.add_argument(
            "--voxel-model",
            dest="voxel_model",
            default="myna_resources/cluster_solidification/voxel_model-sF=0.5-gamma=8",
            type=str,
            help="path to model for voxel clustering",
        )
        self.parser.add_argument(
            "--res",
            default=250.0e-6,
            type=float,
            help="resolution to use for super-voxel size, in meters, for example: --res 250.0e-6",
        )
        super().parse_execute_arguments()

    def execute(self):
        from .execute import run, train_supervoxel_model

        self.parse_execute_arguments()

        try:
            import bnpy
        except ImportError:
            raise ImportError(
                'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
            )

        voxel_model_path = self.args.voxel_model.replace("/", os.sep)
        voxel_model_path = sorted(
            glob.glob(os.path.join(voxel_model_path, "*")), reverse=True
        )[0]
        voxel_model_path = sorted(
            glob.glob(os.path.join(voxel_model_path, "*")), reverse=True
        )[0]
        voxel_model, _ = bnpy.load_model_at_lap(voxel_model_path, None)
        self.n_voxel_clusters = max(voxel_model.allocModel.K, 2)

        myna_files = self.get_step_output_paths()
        cluster_step_name = self.args.cluster
        if cluster_step_name == "":
            cluster_step_name = self.last_step_name
        voxel_cluster_files = self.get_step_output_paths(cluster_step_name)

        supervoxel_composition_filename = "supervoxel_composition.csv"
        self.sF = 0.5
        self.gamma = 8.0
        if self.args.train_model:
            trained_model_path, composition_files = train_supervoxel_model(
                myna_files,
                voxel_cluster_files,
                self,
                comp_file_name=supervoxel_composition_filename,
            )
        else:
            trained_model_path = self.get_latest_model_path()
            composition_files = [
                os.path.join(os.path.dirname(myna_file), supervoxel_composition_filename)
                for myna_file in myna_files
            ]

        print("- Clustering supervoxel data:")
        for myna_file, composition_file in zip(myna_files, composition_files):
            print(f"  - {composition_file=}")
            run(
                myna_file,
                composition_file,
                trained_model_path,
                self,
            )
