import argparse
import os, shutil

from myna.core.workflow.load_input import load_input


class MynaApp:
    settings = "MYNA_RUN_INPUT"
    path = "MYNA_INTERFACE_PATH"
    step_name = "MYNA_STEP_NAME"
    last_step_name = "MYNA_LAST_STEP_NAME"

    def __init__(self, name):
        self.name = name
        self.template = None

        self.settings = load_input(os.environ["MYNA_RUN_INPUT"])
        self.path = os.environ["MYNA_INTERFACE_PATH"]
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
        self.parser.set_defaults(batch=False)

    # Check if executable exists
    def check_exe(self, *path_args):
        exe = self.args.exec
        if exe is None:
            exe = os.path.join(self.path, *path_args)

        if not os.path.exists(exe):
            raise Exception(
                f'The specified {self.name} executable "{exe}" was not found.'
            )
        if not os.access(exe, os.X_OK):
            raise Exception(
                f'The specified {self.name} executable "{exe}" is not executable.'
            )

    # args must have been parsed
    def set_procs(self):
        # Set processor information
        if self.args.maxproc is None:
            self.args.maxproc = os.cpu_count()
        self.args.np = min(os.cpu_count(), self.args.np, self.args.maxproc)

    def set_template_path(self, *path_args):
        if self.template is None:
            self.template = os.path.join(
                self.path,
                *path_args,
                "template",
            )
        else:
            self.template = os.path.abspath(self.template)

    def copy(self, case_dir):
        if (not os.path.exists(self.args.template)) or (self.args.overwrite):
            shutil.copytree(self.args.template, case_dir, dirs_exist_ok=True)
        else:
            print(f"Warning: NOT overwriting existing case in: {case_dir}")
