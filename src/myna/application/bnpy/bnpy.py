#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.app.base import MynaApp
import glob
import os


class Bnpy(MynaApp):
    def __init__(self):
        super().__init__()
        self.app_type = "bnpy"
        self.sF = 0.5
        self.gamma = 8
        self.input_dir = os.path.dirname(self.input_file)
        self.resource_dir = os.path.join(self.input_dir, "myna_resources")
        self.resource_template_dir = None
        self.training_dir = None

    def parse_shared_arguments(self):
        self.parser.add_argument(
            "--model",
            default=None,
            type=str,
            help="path to an existing model to use",
        )
        self.parser.add_argument(
            "--no-training",
            dest="train_model",
            default=True,
            action="store_false",
            help="flag to use pre-trained model",
        )

    def parse_execute_arguments(self):
        self.update_resource_paths()
        self.parse_shared_arguments()
        self.parse_known_args()

    def get_latest_model_path(self):
        latest_model = sorted(
            glob.glob(os.path.join(self.get_model_dir_path(), "*")), reverse=True
        )[0]
        latest_model_iteration = sorted(
            glob.glob(os.path.join(latest_model, "*")), reverse=True
        )[0]
        return latest_model_iteration

    def get_model_dir_path(self):
        model_dir = os.path.join(
            self.resource_template_dir,
            f"{'_'.join(self.name.split('/'))}-sF={self.sF}-gamma={self.gamma}",
        )
        return model_dir

    def make_directory_structure(self):
        os.makedirs(self.resource_template_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)

    def update_resource_paths(self):
        if self.class_name is None:
            return
        self.resource_template_dir = os.path.join(
            self.resource_dir, *self.name.split("/")
        )
        self.training_dir = os.path.join(
            self.resource_template_dir, "training_supervoxels"
        )
        self.make_directory_structure()
