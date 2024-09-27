#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
""" Base class for workflow components"""

import os
import myna
import myna.database
from myna.core.workflow import load_input
import logging


class Component:
    """Base class for a workflow component"""

    step_id = 0

    def __init__(self):
        self.id = Component.step_id
        Component.step_id += 1
        self.component_class = None
        self.component_application = None
        self.configure_dict = {}
        self.execute_dict = {}
        self.postprocess_dict = {}
        self.executable = None
        self.name = f"Component-{self.id}"
        self.data_requirements = []
        self.input_requirement = None
        self.output_requirement = None
        self.input_template = ""
        self.output_template = ""
        self.data = {}
        self.types = ["build"]
        self.workspace = None

    def run_component(self):
        """Runs the configure.py, execute.py, and postprocess.py
        for selected component class & application combination"""

        # Run component configure.py script
        configure_path = os.path.join(
            os.environ["MYNA_APP_PATH"],
            self.component_application,
            self.component_class,
            "configure.py",
        )
        if os.path.exists(configure_path):

            # Submit configure.py command
            cmd = f'python {configure_path} {self.get_step_args_str("configure")}'
            cmd = self.cmd_preformat(cmd)
            os.system(cmd)

        # Run component execute.py script
        has_executed = False
        execute_path = os.path.join(
            os.environ["MYNA_APP_PATH"],
            self.component_application,
            self.component_class,
            "execute.py",
        )
        if os.path.exists(execute_path):
            cmd = f'python {execute_path} {self.get_step_args_str("execute")}'
            cmd = self.cmd_preformat(cmd)
            os.system(cmd)
            has_executed = True

        # Run component postprocess.py script
        postprocess_path = os.path.join(
            os.environ["MYNA_APP_PATH"],
            self.component_application,
            self.component_class,
            "postprocess.py",
        )
        if os.path.exists(postprocess_path):
            cmd = f'python {postprocess_path} {self.get_step_args_str("postprocess")}'
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
        """Replace placeholder names in command arguments and adds executable argument
        if a custom executable path is specified.

        Args:
            raw_cmd: a string of the command with placeholders

        Available placeholders:
            {name}: the name of the component
            {build}: the name of the build associated with the workflow
            $MYNA_APP_PATH: the location of the app module in the myna install
            $MYNA_INSTALL_PATH: the location of the myna installation directory
        """

        cmd = raw_cmd.replace("{name}", self.name)
        cmd = cmd.replace("{build}", self.data["build"]["name"])
        cmd = cmd.replace("$MYNA_APP_PATH", os.environ["MYNA_APP_PATH"])
        cmd = cmd.replace("$MYNA_INSTALL_PATH", os.environ["MYNA_INSTALL_PATH"])

        if self.executable is not None:
            cmd += f" --exec {self.executable}"

        return cmd

    def apply_settings(self, step_settings, data_settings, myna_settings):
        """Update the step and data settings for the component from dictionaries

        Args:
            step_settings: a dictionary of settings related to the myna step
            data_settings: a dictionary of settings related to the build data
            myna_settings: a dictionary of settings related to general Myna functionality
        """

        try:
            # Set workspace path
            if myna_settings is not None:
                self.workspace = myna_settings.get("workspace", None)

            # Load commands for configure, execute, and postprocess
            self.configure_dict = step_settings.get("configure", self.configure_dict)
            self.execute_dict = step_settings.get("execute", self.execute_dict)
            self.postprocess_dict = step_settings.get(
                "postprocess", self.postprocess_dict
            )

            # Set the executable for the step
            if self.workspace is not None:
                workspace_dict = load_input(self.workspace)
                workspace_dict = workspace_dict.get(self.component_application, {})
                workspace_dict = workspace_dict.get(self.component_class, {})
                self.executable = workspace_dict.get("executable", self.executable)
            self.executable = step_settings.get("executable", self.executable)

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

        Sync behavior is defined in the myna.core.workflow.sync functions
        and in the myna.files.File subclasses associated with the Component
        input_requirement and output_requirement properties.

        Returns:
            synced_files: list of filepaths (strings) to the output files
        """

        synced_files = []

        # Check if layerwise syncing is possible
        if "layer" in self.types:
            print("Syncing layer-wise files:")
        elif "region" in self.types:
            print("Syncing region-wise files:")
        else:
            print(f"  - Skipping sync for step {self.name}, no layer-wise fields")
            return synced_files

        # Get output files for the step
        files = self.check_output_files(self.data["output_paths"][self.name])
        datatype = myna.database.return_datatype_class(self.data["build"]["datatype"])
        datatype.set_path(self.data["build"]["path"])

        # Get if there are valid output files to sync
        synced_files = []
        if self.output_requirement is None:
            print(f"- step {self.name}: No output requirement specified.")
        elif len(files) == 0:
            print(f"- step {self.name}: No valid output files found.")
        else:
            # Use the database sync functionality
            synced_files = datatype.sync(
                self.component_application, self.types, self.output_requirement, files
            )

        return synced_files

    def get_step_args_str(self, operation):
        """Get the command string for the configure, execute, or postprocess operation

        Args:
            operation: "configure", "execute", or "postprocess"

        Returns:
            argstr: string of command arguments"""

        # Initialize
        assert operation in set(["configure", "execute", "postprocess"])
        arg_dict = getattr(self, f"{operation}_dict")
        config_str = ""

        # Function to identify obsolete input dictionary keys:
        def check_obsolete_args(dict_key, value, operation):
            obsolete_keys = ["exec"]
            if dict_key in obsolete_keys:
                logging.warn(
                    f" Step {self.name} {operation}"
                    f' argument "{dict_key}" for {operation} is'
                    + " obsolete. Using default value. Instead, use: "
                    + f"  \n\t{self.name}:"
                    + f"  \n\t  executable: {value}\n",
                )
                return True
            else:
                return False

        # Get values from the workspace
        if self.workspace is not None:
            workspace_dict = load_input(self.workspace)
            workspace_dict = workspace_dict.get(self.component_application, {})
            workspace_dict = workspace_dict.get(self.component_class, {})
            workspace_dict = workspace_dict.get(operation, {})
            for key in workspace_dict.keys():
                if key not in arg_dict.keys():
                    value = workspace_dict[key]
                    # Check for flag
                    if (type(workspace_dict[key]) == bool) and (
                        not check_obsolete_args(key, value, operation)
                    ):
                        # Assume that default flag behavior is False
                        if value:
                            config_str += f" --{key}"

                    # Else, get value
                    elif not check_obsolete_args(key, value, operation):
                        config_str += f" --{key} {value}"

        # Overwrite workspace with any values from the input file
        for key in arg_dict.keys():
            value = arg_dict[key]
            if (type(value) == bool) and (
                not check_obsolete_args(key, value, operation)
            ):
                config_str += f" --{key}"
            elif not check_obsolete_args(key, value, operation):
                config_str += f" --{key} {value}"

        return config_str
