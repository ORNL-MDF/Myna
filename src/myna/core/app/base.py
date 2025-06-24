#
# Copyright (c) 2024 Oak Ridge National Laboratory.
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
import shutil
import subprocess
import warnings
from myna.core.workflow.load_input import load_input
from myna.core.utils import is_executable, get_quoted_str


class MynaApp:
    """Myna application base class with functionality that could be used generally by
    any application.

    While applications are not required to inherit this class,
    using the MynaApp functionality where possible for consistent behavior across apps.
    """

    settings = "MYNA_INPUT"
    path = "MYNA_APP_PATH"
    step_name = "MYNA_STEP_NAME"
    last_step_name = "MYNA_LAST_STEP_NAME"

    def __init__(self, name):
        self.name = name
        self.input_file = os.environ["MYNA_INPUT"]
        self.settings = load_input(self.input_file)
        self.path = os.environ["MYNA_APP_PATH"]
        self.step_name = os.environ["MYNA_STEP_NAME"]
        self.last_step_name = os.environ["MYNA_LAST_STEP_NAME"]

        # Set up argparse
        self.parser = argparse.ArgumentParser(
            description=f"Configure {self.name} input files for "
            + "specified Myna cases"
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
            help=f"(str) Path to {self.name} executable",
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
            "--mpiargs",
            default=None,
            type=str,
            help="(str) [WARNING DEPRECATED!] full MPI command with flags, e.g.,"
            "'mpirun --exclusive', excluding the number of processors to use",
        )
        self.parse_known_args()

    def parse_known_args(self):
        """Parse known command line arguments to update self.args and apply
        any corrections"""
        self.args, _ = self.parser.parse_known_args()
        self.set_procs()
        self.mpiargs_to_current()
        if self.args.skip:
            print(f"- Skipping part of step {self.name}")
            sys.exit()

    def mpiargs_to_current(self):
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

    def set_procs(self):
        """Set processor information based on the `maxproc` and `np` inputs. Regardless
        of user inputs, the CPU count will be capped at `os.cpu_count()`
        """
        if self.args.maxproc is None:
            self.args.maxproc = os.cpu_count()
        self.args.np = min(os.cpu_count(), self.args.np, self.args.maxproc)

    def set_template_path(self, *path_args):
        """Set the path to the template directory

        Args:
            path_args: list of path parts to append to `self.path` if no template is
                specified. For example, `path_args=["exaca", "microstructure_region"]`
                gives a template with path
                "{self.path}/exaca/microstructure_region/template"
        """
        if self.args.template is None:
            self.args.template = os.path.join(
                self.path,
                *path_args,
                "template",
            )
        else:
            self.args.template = os.path.abspath(self.args.template)

    def copy(self, case_dir):
        """Copies the set template directory to a case directory, with existing files
        being overwritten depending on the app overwrite user setting.

        Args:
        - case_dir: (str) path to the case directory
        """

        # Get list of files in case directory, except for the myna data file
        try:
            case_dir_files = os.listdir(case_dir)
            case_dir_files.remove("myna_data.yaml")
        except ValueError:
            case_dir_files = []

        # Copy if there are no existing files in the case directory or overwrite is specified
        if (len(case_dir_files) == 0) or (self.args.overwrite):
            shutil.copytree(self.args.template, case_dir, dirs_exist_ok=True)
        else:
            print(f"Warning: NOT overwriting existing case in: {case_dir}")

    def start_subprocess(self, cmd_args, **kwargs):
        """Starts a subprocess, activating an environment if present"""
        if self.args.env is not None:
            popen_args = [f". {self.args.env}; " + " ".join(cmd_args)]
            return subprocess.Popen(popen_args, shell=True, **kwargs)
        return subprocess.Popen(cmd_args, **kwargs)

    def start_subprocess_with_MPI_args(self, cmd_args, **kwargs):
        """Starts a subprocess using `Popen` while taking into account the MynaApp
        MPI-related options. **kwargs are passed to `subprocess.Popen`
        """
        modified_cmd_args = []
        if self.args.mpiexec is not None:
            modified_cmd_args.extend([self.args.mpiexec, "-n", self.args.np])
            if self.args.mpiflags is not None:
                modified_cmd_args.append(self.args.mpiflags)
        modified_cmd_args.extend(cmd_args)
        modified_cmd_args = [str(x) for x in modified_cmd_args]
        return self.start_subprocess(modified_cmd_args, **kwargs)
