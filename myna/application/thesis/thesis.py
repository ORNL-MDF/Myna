import os


class Thesis:
    def __init__(
        self,
        input_dir,
        executable="3DThesis",
        input_filename="ParamInput.txt",
        material_filename="Material.txt",
        output_dir=None,
    ):
        cwd = os.getcwd()

        # Set case directories and input files
        self.input_dir = input_dir
        if output_dir is None:
            self.output_dir = self.input_dir
        else:
            self.output_dir = output_dir
        self.input_file = os.path.join(self.input_dir, input_filename)
        self.material_dir = os.path.join(self.input_dir, material_filename)

        # Set executable path
        self.executable_path = executable

        # Initialize layer and part tracking arrays
        self.layers = []
        self.parts = []
