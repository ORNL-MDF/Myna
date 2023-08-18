''' Subclass for thermal simulations'''
from .component_thermal import *
from myna.files.file_region import *

class ComponentThermalRegion(ComponentThermal):
    def __init__(self):
        ComponentThermal.__init__(self)
        self.input_requirement = FileRegion

    def get_input_files(self, abspath=True):
        build = self.data["build"]["name"]
        files = []
        for part in self.data["parts"]:
            for region in self.data[part]["regions"]:
                input_name = self.input_template
                input_name = input_name.replace("{build}", build)
                input_name = input_name.replace("{name}", name)
                input_name = input_name.replace("{part}", str(part))
                input_name = input_name.replace("{layer}", str(layer))
                str_inputs = [str(x) for x in [build, part, region, input_name]]
                input_path = os.path.join(*str_inputs)
                if abspath: input_path = os.path.abspath(input_path)
                file_obj = self.input_requirement(input_path)
                if file_obj.check_file():
                    files.append(input_path)
                else:
                    print(f"Invalid file for {self.input_requirement}: {input_path}")
                
    def get_output_files(self, abspath=True):
        build = self.data["build"]["name"]
        name = self.name
        files = []
        for part in self.data["parts"]:
            value = self.data["parts"][part].get("regions")
            if value is not None:
                for region in self.data["parts"][part]["regions"]:
                    output_name = self.output_template
                    output_name = output_name.replace("{build}", str(build))
                    output_name = output_name.replace("{name}", str(name))
                    output_name = output_name.replace("{part}", str(part))
                    output_name = output_name.replace("{region}", str(region))
                    str_inputs = [str(x) for x in [build, part, region, self.name, output_name]]
                    output_path = os.path.join(*str_inputs)
                    if abspath: output_path = os.path.abspath(output_path)
                    files.append(output_path)
            else:
                print(f"No regions found in part {part}")
        return files

    def check_output_files(self, files):
        valid_files = []
        for f in files:
            if os.path.isfile(f):
                file_obj = self.output_requirement(f)
                if file_obj.file_is_valid():
                    valid_files.append(f)
                else:
                    print(f"Invalid file for {self.output_requirement}: {f}")
            else:
                print(f"WARNING: Could not find output file {f}")
        return valid_files