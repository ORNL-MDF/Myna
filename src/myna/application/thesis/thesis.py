#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os

from myna.core.app.base import MynaApp


class Thesis(MynaApp):
    def __init__(
        self,
        sim_type,
        input_dir=None,
        input_filename="ParamInput.txt",
        material_filename="Material.txt",
        output_dir=None,
        output_suffix="",
    ):
        super().__init__("3DThesis")
        self.simulation_type = sim_type

        self.parser.add_argument(
            "--res",
            default=12.5e-6,
            type=float,
            help="(float) resolution to use for simulations in meters",
        )
        self.parser.add_argument(
            "--nout",
            default=1000,
            type=int,
            help="(int) number of snapshot outputs",
        )

        self.args = self.parser.parse_args()

        # Set case directories and input files
        self.input_filename = input_filename
        self.material_filename = material_filename
        if input_dir is not None:
            if output_dir is not None:
                self.set_case(input_dir, output_dir)
            else:
                self.set_case(input_dir, input_dir)
        self.output_suffix = output_suffix

        super().set_procs()
        super().check_exe("3DThesis")

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []

    def set_case(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, self.input_filename)
        self.material_dir = os.path.join(self.input_dir, self.material_filename)
