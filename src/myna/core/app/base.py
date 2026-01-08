#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Module to define the base behavior of a Myna simulation application"""

import argparse
import os
import sys
import time
import shutil
import subprocess
import warnings
from pathlib import Path
import docker
from docker.models.containers import Container
from myna.core.workflow.load_input import load_input
from myna.core.utils import is_executable, get_quoted_str
from myna.core.components import return_step_class


class MynaApp:
    """Myna application base class with functionality that could be used generally by
    any application.

    While applications are not required to inherit this class,
    using the MynaApp functionality where possible for consistent behavior across apps.
    """

    # Define ENV class variables that have relevant workflow information
    ENV_SETTINGS_FILE = "MYNA_INPUT"
    ENV_APP_PATH = "MYNA_APP_PATH"
    ENV_STEP_NAME = "MYNA_STEP_NAME"
    ENV_LAST_STEP_NAME = "MYNA_LAST_STEP_NAME"

    def __init__(self):
        # Set the print name as well as the Myna app and class names
        self.class_name: str | None = None
        self.app_type: str | None = None

        # Get the names for the current and previous workflow step
        self.step_name = os.environ.get(self.ENV_STEP_NAME)
        self.last_step_name = os.environ.get(self.ENV_LAST_STEP_NAME)

        # Get the input file contents and parse additional step information
        self.input_file = os.environ.get(self.ENV_SETTINGS_FILE)
        self.settings = {}
        self.step_number = None
        self.template: Path | None = None
        if self.input_file is not None:
            self.settings = load_input(self.input_file)
            self.step_number = [
                list(x.keys())[0] for x in self.settings["steps"]
            ].index(self.step_name)

        # Check if there is a corresponding component class. This will be None if
        # class name is not in the Component lookup dictionary
        if self.class_name is not None:
            self.sim_class_obj = None
            try:
                self.sim_class_obj = return_step_class(self.class_name, verbose=False)
                self.sim_class_obj.apply_settings(
                    self.settings["steps"][self.step_number],
                    self.settings.get("data"),
                    self.settings.get("myna"),
                )
            except KeyError:
                pass

        # Set up argparse
        self.parser = argparse.ArgumentParser(
            description="Configure input files for specified Myna cases"
        )
        self.parser.add_argument(
            "--template",
            default=None,
            type=str,
            help="(str) path to template, if not specified"
            + " then assume default location",
        )
        self.parser.add_argument(
            "--overwrite",
            dest="overwrite",
            default=False,
            action="store_true",
            help="force regeneration of each run and overwrite of any existing data,"
            + " default = False",
        )
        self.parser.add_argument(
            "--exec",
            default=None,
            type=str,
            help="(str) Path to executable",
        )
        self.parser.add_argument(
            "--np",
            default=1,
            type=int,
            help="(int) processors to use per job, will "
            + "correct to the maximum available processors if "
            + "set too large",
        )
        self.parser.add_argument(
            "--maxproc",
            default=None,
            type=int,
            help="(int) maximum available processors for system, will "
            + "correct to the maximum available processors if "
            + "set too large",
        )
        self.parser.add_argument(
            "--batch",
            dest="batch",
            default=False,
            action="store_true",
            help="(flag) run jobs in parallel",
        )
        self.parser.add_argument(
            "--skip",
            dest="skip",
            default=False,
            action="store_true",
            help="(flag) if parsed by the app, skip the corresponding"
            + " stage of the component, default = False",
        )
        self.parser.add_argument(
            "--mpiexec",
            default=None,
            type=str,
            help="(str) MPI executable to prepend for MPI parallel execution"
            + " (for use with --mpiflags)",
        )
        self.parser.add_argument(
            "--mpiflags",
            default=None,
            type=str,
            help="(str) MPI flags to append for MPI parallel execution"
            + " (for use with --mpiexec)",
        )
        self.parser.add_argument(
            "--env",
            default=None,
            type=str,
            help="(str) file to source to set up environment for executable",
        )
        self.parser.add_argument(
            "--docker-image",
            default=None,
            type=str,
            help="(str) Docker image to use to run the app. The executable, "
            "MPI options, and environment file will be applied within "
            "the docker container",
        )
        self.parser.add_argument(
            "--mpiargs",
            default=None,
            type=str,
            help="(str) [WARNING DEPRECATED!] full MPI command with flags, e.g.,"
            "'mpirun --exclusive', excluding the number of processors to use",
        )
        self.parse_known_args()

    @property
    def name(self):
        return f"{self.app_type}/{self.class_name}"

    @property
    def path(self):
        app_path = Path(os.environ.get(self.ENV_APP_PATH, ""))
        if self.app_type is not None:
            app_path = app_path / Path(self.app_type)
        if self.class_name is not None:
            app_path = app_path / Path(self.class_name)
        return app_path

    @property
    def template(self):
        """Set the path to the template directory based on the path to the app directory"""
        if self.args.template is None:
            return Path(self.path) / "template"
        return Path(self.args.template)

    def parse_known_args(self):
        """Parse known command line arguments to update self.args and apply
        any corrections"""
        self.args, _ = self.parser.parse_known_args()
        self._set_procs()
        self._mpiargs_to_current()
        if self.args.skip:
            print(f"- Skipping part of step {self.step_name}")
            sys.exit()

    def _mpiargs_to_current(self):
        """Function to convert the deprecated `--mpiargs` option to the current
        `--mpiexec`, `--np`, and `--mpiflags` options

        TODO: Remove this function in next release"""
        if self.args.mpiargs is not None:
            args = self.args.mpiargs.split(" ")
            self.args.mpiexec = args[0].replace('"', "").replace("'", "")
            del args[0]
            for flag in ["-n", "--n", "-np", "--np"]:
                if flag in args:
                    np_flag_index = args.index(flag)
                    self.args.np = int(args[np_flag_index + 1])
                    del args[np_flag_index + 1]
                    del args[np_flag_index]
                    continue
            self.args.mpiflags = get_quoted_str(" ".join(args))
            warning_msg = (
                f"The deprecated `mpiargs` parameter was used for {self.name}."
                + " Update input file to use separate `mpiexec`, `np`, and `mpiflags`"
                + " parameters. Inputs are interpreted here as\n"
                + f"\t- mpiexec: {self.args.mpiexec}\n"
                + f"\t- np: {self.args.np}\n"
                + f"\t- mpiflags: {self.args.mpiflags}\n"
            )
            warnings.warn(warning_msg, category=DeprecationWarning)

    def validate_executable(self, default):
        """Check if the specified executable exists and raise error if not"""

        # Get the name of the executable
        exe = self.args.exec
        if exe is None:
            exe = default
        exe_windows = exe + ".exe"  # Try a Windows exe just in case

        # If an executable is found, return
        if any(is_executable(x) for x in [exe, exe_windows]):
            return

        # If there is an `env` set, then assume that it sets a valid executable path
        if self.args.env is not None:
            warning_msg = (
                f"Warning: {self.name} app executable was not found,"
                + " but `env` option was set. Assuming the environment sets valid path."
            )
            warnings.warn(warning_msg)
            return

        # If not found, raise the appropriate errors
        if shutil.which(exe, mode=os.F_OK) is None:
            raise FileNotFoundError(
                f'{self.name} app executable "{exe}" was not found.'
            )
        if shutil.which(exe, mode=os.X_OK) is None:
            raise PermissionError(
                f'{self.name} app executable "{shutil.which(exe, mode=os.F_OK)}"'
                + "does not have execute permissions."
            )

    def _set_procs(self):
        """Set processor information based on the `maxproc` and `np` inputs. If the
        available CPU count can be determined by `os.cpu_count()` then it will be used
        as a limiter to avoid oversubscription. If available CPU count cannot be
        determined, then user input will be used as-is.
        """
        os_cpus = os.cpu_count()
        if (self.args.maxproc is None) and (os_cpus is not None):
            self.args.maxproc = os_cpus
            self.args.np = min(self.args.np, self.args.maxproc)
        elif os_cpus is not None:
            self.args.maxproc = min(os_cpus, self.args.maxproc)
            self.args.np = min(self.args.np, self.args.maxproc)

    def copy_template_to_case(self, case_dir):
        """Copies the set template directory to a case directory, with existing files
        being overwritten depending on the app overwrite user setting.

        Args:
        - case_dir: (str) path to the case directory
        """

        # Do not copy anything if no template is set
        if self.template is None:
            raise ValueError(
                f"MynaApp {self.name} self.template property is set to None, "
                "so there is no template to copy"
            )
        if not self.template.exists():
            raise FileNotFoundError(
                f"MynaApp {self.name} self.template '{self.template}' was not found "
                "so there is no template to copy"
            )

        # Get list of files in case directory, except for the myna data file
        try:
            case_dir_files = os.listdir(case_dir)
            case_dir_files.remove("myna_data.yaml")
        except ValueError:
            case_dir_files = []

        # Copy if there are no existing files in the case directory or overwrite is specified
        if (len(case_dir_files) == 0) or (self.args.overwrite):
            shutil.copytree(self.template, case_dir, dirs_exist_ok=True)
        else:
            print(f"Warning: NOT overwriting existing case in: {case_dir}")

    def start_subprocess(self, cmd_args, **kwargs) -> subprocess.Popen | Container:
        """Starts a subprocess, activating an environment if present

        kwargs are passed to the subprocess launcher, Popen or Docker:
            - For Popen subprocess, this can be used to redirect stdout & stderr, etc.
            - For Docker subprocesses, this can be used to pass a volume dictionary,
              whether to remove container after execution, etc.
        """
        # Launch using subprocess.Popen
        if self.args.docker_image is None:
            if self.args.env is not None:
                cmd_arg_str = [f". {self.args.env}; " + " ".join(cmd_args)]
                process = subprocess.Popen(cmd_arg_str, shell=True, **kwargs)
                print(f"myna subprocess (PID {process.pid}): {cmd_arg_str}")
                return process
            process = subprocess.Popen(cmd_args, **kwargs)
            print(f"myna subprocess (PID {process.pid}): {cmd_args}")
            return process

        # Launch using Docker, overriding any default entrypoint by using bash
        cmd_arg_str = " ".join(cmd_args)
        if self.args.env is not None:
            cmd_arg_str = f". {self.args.env}; " + cmd_arg_str
        cmd_arg_str = f"-c '{cmd_arg_str}'"
        client = docker.from_env()
        process = client.containers.run(
            self.args.docker_image,
            cmd_arg_str,
            entrypoint="bash",
            detach=True,
            **kwargs,
        )
        print(
            f"myna docker container {self.args.docker_image} ({process.name}):"
            f" {cmd_arg_str}"
        )
        return process

    def start_subprocess_with_mpi_args(self, cmd_args, **kwargs):
        """Starts a subprocess using `Popen` while taking into account the MynaApp
        MPI-related options. **kwargs are passed to `subprocess.Popen`
        """
        modified_cmd_args = []
        if self.args.mpiexec is not None:
            modified_cmd_args.extend([self.args.mpiexec, "-n", self.args.np])
            if self.args.mpiflags is not None:
                split_flags = self.args.mpiflags[1:-1].strip().split(" ")
                modified_cmd_args.extend(split_flags)
        modified_cmd_args.extend(cmd_args)
        modified_cmd_args = [str(x) for x in modified_cmd_args]
        return self.start_subprocess(modified_cmd_args, **kwargs)

    def wait_for_process_success(
        self, process: subprocess.Popen | Container, raise_error=True
    ):
        """Wait for a process to complete successfully, raising an error if the
        process fails.

        Args:
            process: (subprocess.Popen) subprocess object
            raise_error: (bool) if True, a failed subprocess will raise an error

        Returns:
            returncode: (int) process returncode from `Popen.wait()`
        """

        # Both subprocess.Popen and the docker Container class have the .wait() method
        returncode = process.wait()
        if isinstance(process, Container):
            returncode = returncode["StatusCode"]
        if returncode != 0:
            error_msg = (
                f"{self.name}: Subprocess exited with return code {returncode}."
                + " Check case log files for details."
            )
            if raise_error:
                raise subprocess.SubprocessError(error_msg)
        return returncode

    def wait_for_all_process_success(self, processes, raise_error=True):
        """Wait for a process to complete successfully, raising an error if the
        process fails.

        Args:
            process: (subprocess.Popen) subprocess object
            raise_error: (bool) if True, a failed subprocess will raise an error

        Returns:
            returncode: (int) process returncode from `Popen.wait()`
        """

        returncodes = []
        error_msg = ""
        for process in processes:
            returncodes.append(
                self.wait_for_process_success(process, raise_error=False)
            )
        if any(returncodes):
            error_msg = (
                f"{self.name}: Batch subprocesses exited with return codes {returncodes}."
                + " Check corresponding case log files for details."
            )
            if raise_error:
                raise subprocess.SubprocessError(error_msg)

    def wait_for_open_batch_resources(
        self, processes: list[subprocess.Popen | Container], poll_interval=1
    ):
        """Given a list of subprocesses, checks if there are available resources
        to run another subprocess. If there are no open resources, then will wait
        to return until there are.

        > [!warning]
        > When running in batch mode with MPI options, this will be ignored

        Args:
            processes: (list) of subprocess.Popen objects
            poll_interval: (float) time to wait between process polls, in seconds
        """

        # If MPI arguments were specified assume that local resources, i.e.,
        # `self.args.maxproc` are not accurate and that MPI is responsible for throwing
        # errors about oversubscription of resources
        open_resources = False
        if self.args.mpiexec is not None:
            open_resources = True

        while not open_resources:
            procs_in_use = 0
            for process in processes:
                # Add `self.args.np` to processors in use if process is still running
                if isinstance(process, subprocess.Popen):
                    # .poll() will return None is process is still running
                    if process.poll() is None:
                        procs_in_use += self.args.np
                elif isinstance(process, Container):
                    # status will return either "running" or "exited"
                    process.reload()
                    if str(process.status).lower() == "running":
                        procs_in_use += self.args.np
            open_resources = procs_in_use <= (self.args.maxproc - self.args.np)
            if not open_resources:
                time.sleep(poll_interval)
