#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines myna launch_peregrine functionality"""

import os
import subprocess
import datetime
import yaml
import shutil
from myna.core.utils import working_directory
from .load_input import write_input


def launch_from_peregrine(parser):
    # Set working directory to the peregrine_launcher interface
    peregrine_launcher_path = os.path.join(
        os.environ["MYNA_INSTALL_PATH"], "cli", "peregrine_launcher"
    )

    parser.add_argument(
        "--build",
        default=None,
        nargs="+",
        type=str,
        help="path to the desired build to simulate",
    )
    parser.add_argument(
        "--parts",
        default=None,
        type=lambda s: [str(item) for item in s.strip()[1:-1].split(",")],
        help="list of part names to simulate",
    )
    parser.add_argument(
        "--layers",
        default=None,
        type=lambda s: [int(item) for item in s.strip()[1:-1].split(",")],
        help="list of layers to simulate",
    )
    parser.add_argument(
        "--workspace",
        default=None,
        nargs="+",
        type=str,
        help="path to the desired workspace to use",
    )
    parser.add_argument(
        "--mode",
        default=None,
        type=str,
        help="simulation mode to use",
    )
    parser.add_argument(
        "--tmp-dir",
        default="/mnt/peregrine",
        type=str,
        help="directory to create Myna_Temporary_Files folder to store temporary files, cannot contain spaces",
    )

    args = parser.parse_args()

    # Parse the arguments passed from Peregrine
    layers = args.layers
    exported_parts = args.parts
    mode = args.mode
    tmp_dir = args.tmp_dir

    # For paths, handle spaces by parsing as lists of arguments
    build_path = os.path.abspath(" ".join(args.build))
    workspace = os.path.abspath(" ".join(args.workspace))

    # Check if build path includes Peregrine as the last directory
    if any([build_path[-1] == sep for sep in [os.path.sep, os.path.altsep]]):
        build_path = build_path[:-1]
    if os.path.basename(build_path) == "Peregrine":
        build_path = os.path.dirname(build_path)

    # Write Peregrine input to log file lines
    lines = []
    lines.append("Peregrine inputs:\n")
    lines.append(f"- {build_path=}\n")
    lines.append(f"- {layers=}\n")
    lines.append(f"- {exported_parts=}\n")
    lines.append(f"- {mode=}\n")
    lines.append(f"- {workspace=}\n")

    # Get yyyy-mm-dd_hh-mm format for the current time and add to log file
    now = datetime.datetime.now()
    now_str_pretty = now.strftime("%Y-%m-%d %H:%M:%S")
    now_str_id = now.strftime("%Y-%m-%d-%Hh-%Mm")
    lines.append(f"\nSimulation started at {now_str_pretty}\n")

    # Create a temp Myna working directory in the tmp_dir if it doesn't already exist
    myna_working_dir = os.path.join(tmp_dir, "Myna_Temporary_Files", now_str_id)
    os.makedirs(myna_working_dir, exist_ok=True)

    # Set input file paths
    input_file = os.path.join(peregrine_launcher_path, f"input_{mode}.yaml")
    input_file_configured = os.path.join(
        myna_working_dir, f"input_{mode}_{now_str_id}.yaml"
    )

    # Read and update input dictionary
    output_dir = os.path.basename(build_path).replace(" ", "_") + f"_{now_str_id}"
    with open(input_file, "r") as f:
        input_dict = yaml.safe_load(f)
    input_dict["data"] = {}
    input_dict["data"]["build"] = {}
    input_dict["data"]["build"]["datatype"] = "Peregrine"
    input_dict["data"]["build"]["name"] = output_dir
    input_dict["data"]["build"]["path"] = build_path
    input_dict["data"]["build"]["parts"] = {}
    for part in exported_parts:
        input_dict["data"]["build"]["parts"][part] = {"layers": layers}
    input_dict["myna"] = {}
    input_dict["myna"]["workspace"] = workspace

    # Export updated input dictionary
    write_input(input_dict, input_file_configured)

    # Set working directory to run all myna scripts
    with working_directory(myna_working_dir):
        # Construct myna config command
        lines.append("\nStarting configuration of simulation cases:\n")
        cmd = f'myna config --input "{input_file_configured}"'
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = p.stdout.decode()

        # Add time to log file
        now_str_pretty = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"\nSync to Peregrine completed at {now_str_pretty}\n")

        # Parse output to store in log file
        lines.append(f"{cmd=}\n\n")
        for line in out.split("\r\n"):
            print(line)
            lines.append(line + "\n")
        lines.append("\n")

        # Construct myna run command
        lines.append("\nStarting simulation pipeline execution:\n")
        cmd = f'myna run --input "{input_file_configured}"'
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = p.stdout.decode()

        # Parse output
        lines.append(f"{cmd=}\n\n")
        for line in out.split("\r\n"):
            print(line)
            lines.append(line + "\n")
        lines.append("\n")

        # Add time to log file
        now_str_pretty = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"\nSimulation completed at {now_str_pretty}\n")

        # Construct myna sync command
        lines.append("Syncing simulation results to Peregrine:\n")
        cmd = f'myna sync --input "{input_file_configured}"'
        p = subprocess.run(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        out = p.stdout.decode()

        # Parse output
        lines.append(f"{cmd=}\n\n")
        for line in out.split("\r\n"):
            print(line)
            lines.append(line + "\n")
        lines.append("\n")

        # Add time to log file
        now_str_pretty = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"\nSync to Peregrine completed at {now_str_pretty}\n")

        # Write log file
        with open(f"launch_from_peregrine_{now_str_id}.log", "w") as f:
            f.writelines(lines)

    # Copy temporary files to the build directory
    myna_build_dir = os.path.join(build_path, "Myna")
    shutil.copytree(myna_working_dir, myna_build_dir, dirs_exist_ok=True)

    # Clean the temporary directory
    shutil.rmtree(myna_working_dir)
