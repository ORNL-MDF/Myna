#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.core.workflow.load_input import load_input
import argparse
import sys
import shutil
import os


def setup_case(case_dir, template_dir):

    # Set template path
    if template_dir is None:
        template_path = os.path.join(
            os.environ["MYNA_INTERFACE_PATH"],
            "openfoam",
            "mesh_part_vtk",
            "template",
        )
    else:
        template_path = os.path.abspath(template_dir)

    shutil.copytree(template_path, case_dir, dirs_exist_ok=True)


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Configure case directories for meshing operations based on"
        + "the specified input file"
    )
    parser.add_argument(
        "--template",
        type=str,
        help="(str) path to template, if not specified"
        + " then assume default location",
    )

    # Parse command line arguments and get Myna settings
    args = parser.parse_args(argv)
    settings = load_input(os.environ["MYNA_RUN_INPUT"])
    template = args.template

    # Get expected Myna output files to identify output directories
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Copy OpenFOAM template files needed for meshing for each Myna case
    output_files = []
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        output_files.append(
            setup_case(
                case_dir,
                template,
            )
        )


if __name__ == "__main__":
    main(sys.argv[1:])
