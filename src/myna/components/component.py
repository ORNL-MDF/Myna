''' Base class for workflow components'''
import os

class Component:
    ''' Base class for a workflow component'''
    step_id = 0

    def __init__(self):
        self.id = Component.step_id
        Component.step_id += 1
        self.configure = []
        self.execute = []
        self.postprocess = []
        self.name = f"Component {self.id}"
        self.data_requirements = []
        self.input_requirement = None
        self.output_requirement = None
        self.input_template = ""
        self.output_template = ""
        self.data = {}

    def run_component(self):

        # Run component configuration
        if len(self.configure) > 0:
            for raw_cmd in self.configure:
                cmd = self.cmd_preformat(raw_cmd)
                os.system(cmd)

        # Execute component
        has_executed = False
        if len(self.execute) > 0:
            for raw_cmd in self.execute:
                cmd = self.cmd_preformat(raw_cmd)
                os.system(cmd)
            has_executed = True

        # Run component postprocessing
        if len(self.postprocess) > 0:
            for raw_cmd in self.postprocess:
                cmd = self.cmd_preformat(raw_cmd)
                os.system(cmd)

        # Check output of component
        output_files = self.get_output_files()
        if len(output_files) > 0:
            if has_executed:
                valid_output_files = self.check_output_files(output_files)
                if (len(valid_output_files) == len(output_files)):
                    print(f"All output files are valid for step {self.name}.")
                else:
                    print(f"Found {len(valid_output_files)} valid output files out of {len(output_files)}" 
                        + f" output files for step {self.name}. Expected output files:")
                    [print("\t" + x) for x in output_files]
                    raise IOError
            else:
                print(f"No execute command was specified for step {self.name}. The expected output files are:")
                [print("\t" + x) for x in output_files]

    def cmd_preformat(self, raw_cmd):
        cmd = raw_cmd.replace("{name}", self.name)
        cmd = cmd.replace("{build}", self.data["build"]["name"])
        return cmd

    def apply_settings(self, step_settings, data_settings):
        try:
            self.configure = step_settings["configure"]
            self.execute = step_settings["execute"]
            self.postprocess = step_settings["postprocess"]
            self.output_template = step_settings["output_template"]
            self.data = data_settings
        except KeyError as e:
            print(e)
            print("ERROR: Check input file contains necessary fields for all steps.")
            print("Required fields are:")
            print("- configure")
            print("- execute")
            print("- postprocess")
            print("- output_template")
            exit()

    def get_input_files(self):
        '''Return input file paths associated with the component.'''
        raise NotImplementedError

    def get_output_files(self):
        '''Return output file paths associated with the component.'''
        raise NotImplementedError

    def check_output_files(self, files):
        '''Return whether a list of output files is valid for the component.'''
        raise NotImplementedError

        
        
    



