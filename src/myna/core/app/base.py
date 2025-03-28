#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import argparse
import os, shutil
from myna.core.workflow.load_input import load_input
from myna.core.utils import is_executable


class MynaApp:
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
            default="mpiexec",
            type=str,
            help="(str) MPI executable to prepend for MPI parallel execution"
            + " (for use with --mpiflags)",
        )
        self.parser.add_argument(
            "--mpiflags",
            default="",
            type=str,
            help="(str) MPI flags to append for MPI parallel execution"
            + " (for use with --mpiexec)",
        )
        self.args, _ = self.parser.parse_known_args()

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

        # If not found, raise the appropriate errors
        if shutil.which(exe, mode=os.F_OK) is None:
            raise FileNotFoundError(
                f'{self.name} app executable "{exe}" was not found.'
            )
        if shutil.which(exe, mode=os.X_OK) is None:
            raise PermissionError(
                f'{self.name} app executable "{shutil.which(exe, mode=os.F_OK)}" does not have execute permissions.'
            )

    # args must have been parsed
    def set_procs(self):
        # Set processor information
        if self.args.maxproc is None:
            self.args.maxproc = os.cpu_count()
        self.args.np = min(os.cpu_count(), self.args.np, self.args.maxproc)

    def set_template_path(self, *path_args):
        if self.args.template is None:
            self.args.template = os.path.join(
                self.path,
                *path_args,
                "template",
            )
        else:
            self.args.template = os.path.abspath(self.args.template)

    def copy(self, case_dir):

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
