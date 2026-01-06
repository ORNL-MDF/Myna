#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.app.base import MynaApp
from myna.core.workflow.load_input import load_input
import glob
import os


class Bnpy(MynaApp):
    def __init__(self, app_type="bnpy", class_name=None):
        super().__init__(app_type, class_name)
        self.simulation_type = app_type if class_name is None else class_name
        self.sF = 0.5
        self.gamma = 8
        self.settings = load_input(os.environ["MYNA_INPUT"])
        self.input_dir = os.path.dirname(os.environ["MYNA_INPUT"])
        self.resource_dir = os.path.join(self.input_dir, "myna_resources")
        self.resource_template_dir = os.path.join(
            self.resource_dir, self.simulation_type
        )
        self.training_dir = os.path.join(
            self.resource_template_dir, "training_supervoxels"
        )
        self.make_directory_structure()

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
            f"{self.simulation_type}-sF={self.sF}-gamma={self.gamma}",
        )
        return model_dir

    def make_directory_structure(self):
        os.makedirs(self.resource_template_dir, exist_ok=True)
        os.makedirs(self.training_dir, exist_ok=True)
