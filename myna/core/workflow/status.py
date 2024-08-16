#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Functionality to output information about available modules in Myna
to a text file
"""

from myna import core
from importlib.metadata import version
import os


# Parser comes from the top-level command parsing
def write_codebase_status_to_file(parser):
    """Writes available Myna components, data, files, and interfaces
    to a file
    """
    parser.add_argument(
        "--output",
        nargs="?",
        type=str,
        default="status.md",
        help="path to the desired output file to generate"
        + ", default: "
        + "--output status.md",
    )

    # Parse cmd arguments
    args = parser.parse_args()
    output_file = args.output

    # Print header
    lines = []
    lines.append("# Status of Myna components and applications\n\n")
    lines.append(f'Myna version: {version("myna")}\n')

    # Get all components classes
    obj = core.components
    lines.append("\nWorkflow components:\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                suffix = ""
                obj_type = obj_inst.__mro__[-2]
                if len(obj_inst.__mro__) == 2:
                    suffix = " (base class)"
                if obj_type == obj.component.Component:
                    lines.append(f"- {key}{suffix}\n")
            except Exception:
                pass

    # Get all file classes
    obj = core.files
    lines.append("\nAvailable file classes:\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                suffix = ""
                obj_type = obj_inst.__mro__[-2]
                if len(obj_inst.__mro__) == 2:
                    suffix = " (base class)"
                if obj_type == obj.file.File:
                    lines.append(f"- {key}{suffix}\n")
            except Exception:
                pass

    # Get all metadata classes
    obj = core.metadata
    lines.append("\nAvailable metadata classes:\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                suffix = ""
                obj_type = obj_inst.__mro__[-2]
                if len(obj_inst.__mro__) == 2:
                    suffix = " (base class)"
                if obj_type == obj.data.BuildMetadata:
                    lines.append(f"- {key}{suffix}\n")
            except Exception:
                pass

    # Get all applications
    path = os.environ["MYNA_INTERFACE_PATH"]
    basepath = os.environ["MYNA_INSTALL_PATH"]
    lines.append("\nAvailable applications:\n\n")
    for root, dirs, files in os.walk(path):
        root_simple = root.replace(basepath + os.path.sep, "")
        depth = len(root_simple.split(os.path.sep))
        if depth == 2:
            lines.append(f"- {os.path.basename(root)}\n")
        if depth == 3:
            lines.append(f"  - {os.path.basename(root)}\n")

    with open(output_file, "w") as f:
        f.writelines(lines)
