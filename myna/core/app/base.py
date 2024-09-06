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


class MynaApp:
    settings = "MYNA_RUN_INPUT"
    path = "MYNA_APP_PATH"
    step_name = "MYNA_STEP_NAME"
    last_step_name = "MYNA_LAST_STEP_NAME"

    def __init__(self, name):
        self.name = name
        self.settings = load_input(os.environ["MYNA_RUN_INPUT"])
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
            type=str,
            help="(str) path to template, if not specified"
            + " then assume default location",
        )
        self.parser.add_argument(
            "--overwrite",
            dest="overwrite",
            action="store_true",
            help="force regeneration of each run and overwrite of any existing data",
        )
        self.parser.set_defaults(overwrite=False)
        self.parser.add_argument(
            "--exec", type=str, help=f"(str) Path to {self.name} executable"
        )
        self.parser.add_argument(
            "--np",
            default=8,
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
            action="store_true",
            help="(flag) run jobs in parallel",
        )
        self.parser.add_argument(
            "--skip",
            dest="batch",
            action="store_true",
            help="(flag) run jobs in parallel",
        )
        self.parser.set_defaults(batch=False)
        self.parser.set_defaults(skip=False)

    # Check if executable exists
    def check_exe(self, default):
        # Try user-specified location or find it in the PATH.
        exe = self.args.exec
        # Try to find it in the path.
        if exe is None:
            exe = shutil.which(default)
            # Try a Windows exe just in case.
            if exe is None:
                exe = shutil.which(default + ".exe")

            if exe is None or not os.path.exists(exe):
                raise Exception(f"{self.name} executable was not found.")
        else:
            exe = shutil.which(exe)

        # Check that it can be used
        if not os.access(exe, os.X_OK):
            raise Exception(f'{self.name} executable "{exe}" is not executable.')

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
