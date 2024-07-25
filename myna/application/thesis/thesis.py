import os
from myna.application.base import MynaApp


class Thesis(MynaApp):
    def __init__(
        self,
        sim_type,
        argv,
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

        self.args = self.parser.parse_args(argv)

        # Set case directories and input files
        if input_dir is not None:
            if output_dir is not None:
                self.set_case(input_dir, output_dir)
            else:
                self.set_case(input_dir, input_dir)
        self.input_filename = input_filename
        self.material_filename = material_filename
        self.output_suffix = output_suffix

        super().set_procs()
        super().check_exe(
            "thesis",
            self.simulation_type,
            "3DThesis",
            "build",
            "application",
            "3DThesis.exe",
        )

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []

    def set_case(self, input_dir, output_dir):
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, self.input_filename)
        self.material_dir = os.path.join(self.input_dir, self.material_filename)
