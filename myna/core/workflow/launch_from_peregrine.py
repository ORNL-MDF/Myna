#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines myna launch_peregrine functionality"""

import sys
import os
import subprocess
import datetime
import contextlib
from pathlib import Path
import yaml
import myna.core.utils


@contextlib.contextmanager
def working_directory(path):
    """
    Changes working directory and returns to previous on exit.

    Reference:
    - https://stackoverflow.com/questions/41742317/how-can-i-change-directory-with-python-pathlib
    """
    prev_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def launch_from_peregrine(parser):
    # Set working directory to the peregrine_launcher interface
    peregrine_launcher_path = os.path.join(
        os.environ["MYNA_INSTALL_PATH"], "cli", "peregrine_launcher"
    )

    parser.add_argument(
        "--build",
        default=None,
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
        type=str,
        help="path to the desired workspace to use",
    )
    parser.add_argument(
        "--mode",
        default=None,
        type=str,
        help="simulation mode to use",
    )

    args = parser.parse_args()

    # Parse the arguments passed from Peregrine
    build_path = os.path.abspath(args.build)
    layers = args.layers
    exported_parts = args.parts
    mode = args.mode
    workspace = os.path.abspath(args.workspace)

    # Check if build path includes Peregrine as the last directory
    if any([build_path[-1] == sep for sep in [os.path.sep, os.path.altsep]]):
        build_path = build_path[:-1]
    if os.path.basename(build_path) == "Peregrine":
        build_path = os.path.dirname(build_path)

    # Create Myna directory if it doesn't already exist
    myna_working_dir = os.path.join(build_path, "Myna")
    os.makedirs(myna_working_dir, exist_ok=True)

    # Write Peregrine input to log file
    lines = []
    lines.append(f"Peregrine inputs:\n")
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
    with open(input_file_configured, "w") as f:
        yaml.dump(input_dict, f, default_flow_style=False)

    # Set working directory to run all myna scripts
    with working_directory(myna_working_dir):

        # Construct myna config command
        lines.append("\nStarting configuration of simulation cases:\n")
        cmd = f"myna config --input {input_file_configured}"
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
        cmd = f"myna run --input {input_file_configured}"
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
        cmd = f"myna sync --input {input_file_configured}"
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
