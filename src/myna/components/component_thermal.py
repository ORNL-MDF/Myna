''' Subclass for thermal simulations'''
from .component import *
from myna.files.file_gv import *

class ComponentThermal(Component):
    def __init__(self):
        Component.__init__(self)
        self.data_requirements.extend(
            ["spot_size",
            "laser_power",
            "preheat",
            "material"]
        )
        self.output_requirement = FileGV

    def get_output_files(self, abspath=True):
        build = self.data["build"]["name"]
        name = self.name
        files = []
        for part in self.data["parts"]:
            for layer in self.data["parts"][part]["layers"]:
                output_name = self.output_template
                output_name = output_name.replace("{build}", build)
                output_name = output_name.replace("{name}", name)
                output_name = output_name.replace("{part}", str(part))
                output_name = output_name.replace("{layer}", str(layer))
                str_inputs = [str(x) for x in [build, part, layer, name, output_name]]
                output_path = os.path.join(*str_inputs)
                if abspath: output_path = os.path.abspath(output_path)
                files.append(output_path)
        return files

    def check_output_files(self, files):
        valid_files = []
        for f in files:
            file_obj = self.output_requirement(f)
            if file_obj.file_is_valid():
                valid_files.append(f)
            else:
                print(f"Invalid file for {self.output_requirement}: {f}")
        return valid_files
