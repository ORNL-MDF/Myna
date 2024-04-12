""" Base class for workflow components"""

import os
import myna


class Component:
    """Base class for a workflow component"""

    step_id = 0

    def __init__(self):
        self.id = Component.step_id
        Component.step_id += 1
        self.component_class = None
        self.component_interface = None
        self.configure_args = []
        self.execute_args = []
        self.postprocess_args = []
        self.name = f"Component-{self.id}"
        self.data_requirements = []
        self.input_requirement = None
        self.output_requirement = None
        self.input_template = ""
        self.output_template = ""
        self.data = {}
        self.types = ["build"]

    def run_component(self):
        """Runs the configure.py, execute.py, and postprocess.py
        for selected component class/interface combination"""

        # Run component configure.py script
        configure_path = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            self.component_class,
            self.component_interface,
            "configure.py",
        )
        if os.path.exists(configure_path):
            cmd = f'python {configure_path} {" ".join(self.configure_args)}'
            cmd = self.cmd_preformat(cmd)
            os.system(cmd)

        # Run component execute.py script
        has_executed = False
        execute_path = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            self.component_class,
            self.component_interface,
            "execute.py",
        )
        if os.path.exists(execute_path):
            cmd = f'python {execute_path} {" ".join(self.execute_args)}'
            cmd = self.cmd_preformat(cmd)
            os.system(cmd)
            has_executed = True

        # Run component postprocess.py script
        postprocess_path = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            self.component_class,
            self.component_interface,
            "postprocess.py",
        )
        if os.path.exists(postprocess_path):
            cmd = f'python {postprocess_path} {" ".join(self.postprocess_args)}'
            cmd = self.cmd_preformat(cmd)
            os.system(cmd)

        # Check output of component
        output_files, exists, valid = self.get_output_files()
        if len(output_files) > 0:
            if has_executed:
                if all(valid):
                    print(f"All output files are valid for step {self.name}.")
                else:
                    print(
                        f"WARNING: Only found {sum(valid)} valid output files out of {len(output_files)}"
                        + f" output files for step {self.name}. Expected output files:"
                    )
                    [print("\t" + x) for x in output_files]
            else:
                print(
                    f"No execute command was specified for step {self.name}. The expected output files are:"
                )
                [print("\t" + x) for x in output_files]

    def cmd_preformat(self, raw_cmd):
        """Replace placeholder names in command arguments

        Args:
            raw_cmd: a string of the command with placeholders

        Available placeholders:
            {name}: the name of the component
            {build}: the name of the build associated with the workflow
            $MYNA_INTERFACE_PATH: the location of the interfaces for the myna install
            $MYNA_INSTALL_PATH: the location of the myna installation directory
        """

        cmd = raw_cmd.replace("{name}", self.name)
        cmd = cmd.replace("{build}", self.data["build"]["name"])
        cmd = cmd.replace("$MYNA_INTERFACE_PATH", os.environ["MYNA_INTERFACE_PATH"])
        cmd = cmd.replace("$MYNA_INSTALL_PATH", os.environ["MYNA_INSTALL_PATH"])
        return cmd

    def apply_settings(self, step_settings, data_settings):
        """Update the step and data settings for the component from dictionaries

        Args:
            step_settings: a dictionary of settings related to the myna step
            data_settings: a dictionary of settings related to the build data
        """

        try:
            # Load commands for configure, execute, and postprocess
            self.configure_args = step_settings.get(
                "configure_args", self.configure_args
            )
            self.execute_args = step_settings.get("execute_args", self.execute_args)
            self.postprocess_args = step_settings.get(
                "postprocess_args", self.postprocess_args
            )

            # If an output_template is specified, use it.
            # Otherwise, use a combination of the class, component, and output names.
            self.output_template = step_settings.get(
                "output_template", self.output_template
            )
            if self.output_template == "" or self.output_template is None:
                filetype = ""
                self.output_template = step_settings.get("class", "")
                if self.output_requirement is not None:
                    filetype = self.output_requirement("").filetype
                    self.output_template += (
                        f"-{self.name}-{self.output_requirement.__name__}{filetype}"
                    )

            # Set myna data
            self.data = data_settings

        except KeyError as e:
            print(e)
            print("ERROR: Check input file contains necessary fields for all steps.")

    def get_files_from_template(self, template, abspath=True):
        """Get all possible input files associated with the component

        Args:
            template: string that will be used for the output file name for each case
            abspath: boolean for using absolute path (True, default) or relative (False)
        """

        files = []

        # Get build name
        build = self.data["build"]["name"]

        # Get all other names that are set by the component
        vars = self.types[1:]
        vars_symbols = [f"{{{x}}}" for x in vars]

        # Get all possible file names based on template
        if len(vars) >= 1:
            parts = None
            regions = None
            layers = []
            if "part" in vars:
                parts = list(self.data["build"]["parts"].keys())
            if parts is not None:
                for part in parts:
                    if "region" in vars:
                        try:
                            regions = list(
                                self.data["build"]["parts"][part]["regions"].keys()
                            )
                        except:
                            print("    - No regions specified in input file")
                            return []
                    if regions is not None:
                        for region in regions:
                            r = self.data["build"]["parts"][part]["regions"][region]
                            if "layer" in vars:
                                layers = r["layers"]
                                filelist = [
                                    os.path.join(
                                        build, part, region, str(x), self.name, template
                                    )
                                    for x in layers
                                ]
                            else:
                                filelist = [
                                    os.path.join(
                                        build, part, region, self.name, template
                                    )
                                ]
                            files.extend(filelist)
                    else:
                        if "layer" in vars:
                            layers = self.data["build"]["parts"][part]["layers"]
                            filelist = [
                                os.path.join(build, part, str(x), self.name, template)
                                for x in layers
                            ]
                        else:
                            filelist = [os.path.join(build, part, self.name, template)]
                        files.extend(filelist)

        elif len(self.types) == 1:
            files.append(os.path.join(build, self.name, template))

        else:
            print(
                f"- step {self.name}: No component type specified. Cannot locate output files."
            )

        # Update template symbols with actual values
        for i in range(len(files)):
            for var_symbol, var in zip(vars_symbols, vars):
                files[i] = files[i].replace(var_symbol, var)
            if abspath:
                files[i] = os.path.abspath(files[i])

        return files

    def get_input_files(self, last_step_obj):
        """Return input file paths associated with the component.

        Args:
            last_step_obj: myna.components.component.Component object for the last
              step in the workflow
        """

        files, exists, valid = last_step_obj.get_output_files()

        return files, exists, valid

    def get_output_files(self, abspath=True):
        """Return output file paths associated with the component.

        Args:
            abspath: default True, boolean for using absolute (True) or relative (False) paths
        """

        # Get output files based on template
        files = self.get_files_from_template(self.output_template, abspath=abspath)
        exists = []
        valid = []

        for f in files:
            # Check if output file exists and is valid
            if os.path.exists(f):
                exists.append(True)
                file_obj = self.output_requirement(f)
                valid.append(file_obj.file_is_valid())
            else:
                exists.append(False)
                valid.append(False)

        return files, exists, valid

    def check_output_files(self, files):
        """Return whether a list of output files is valid for the component.

        Args:
            files: list of filepaths (strings) to check for validity
        """
        valid_files = []
        if (self.output_requirement is None) or (len(files) == 0):
            print(f"- step {self.name}: No output requirement specified.")
            return valid_files
        else:
            for f in files:
                if os.path.isfile(f):
                    file_obj = self.output_requirement(f)
                    if file_obj.file_is_valid():
                        valid_files.append(f)
                    else:
                        print(
                            f"- step {self.name}: Invalid file for {self.output_requirement} -- {f}"
                        )
                else:
                    print(f"- step {self.name}: Could not find output file -- {f}")
        return valid_files

    def sync_output_files(self):
        """Sync valid output files back to the database

        Sync behavior is defined in the myna.workflow.sync functions
        and in the myna.files.File subclasses associated with the Component
        input_requirement and output_requirement properties.

        Returns:
            synced_files: list of filepaths (strings) to the output files
        """

        synced_files = []

        # Check if layerwise syncing is possible
        if "layer" not in self.types:
            print(f"  - Skipping sync for step {self.name}, no layer-wise fields")
            return synced_files
        else:
            print("Syncing files:")

        # Get output files for the step
        files = self.check_output_files(self.data["output_paths"][self.name])
        datatype = self.data["build"]["datatype"]
        buildpath = self.data["build"]["path"]
        if self.output_requirement is None:
            print(f"- step {self.name}: No output requirement specified.")
        elif len(files) == 0:
            print(f"- step {self.name}: No valid output files found.")
        else:
            for f in files:
                print(f"- {f}")

                # Get output file fields to export
                output_file_obj = self.output_requirement(f)
                (
                    x,
                    y,
                    values,
                    value_names,
                    value_units,
                ) = output_file_obj.get_values_for_sync(
                    prefix=f"myna_{self.component_interface}"
                )

                # Get metadata from file path
                split_path = f.split(os.path.sep)
                interface = split_path[-2]
                layer = int(split_path[-3])
                part = split_path[-4]

                # Iterate through loaded fields
                for value, name, unit in zip(values, value_names, value_units):
                    print(f"  - field: {name}")
                    if datatype == "Peregrine":
                        peregrine_dir = os.path.join(buildpath, "Peregrine")
                        output_dir = os.path.join(peregrine_dir, "registered", name)
                        partnumber = int(part.replace("P", ""))
                        output_file = myna.workflow.sync.upload_peregrine_results(
                            peregrine_dir,
                            partnumber,
                            layer,
                            x,
                            y,
                            value,
                            var_name=name,
                            var_unit=unit,
                            output_path=output_dir,
                        )
                        print(f"     - output_file: {output_file=}")
                        synced_files.append(output_file)

        return synced_files
