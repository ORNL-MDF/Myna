#
# Copyright (c) Oak Ridge National Laboratory.
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


def format_class_string_to_list(
    object_instance, label, include_types=None, branch="main"
):
    """Turns the class object into a formatted list item

    Args:
      object_instance: instance of the class object
      label: name of the class object
      include_types: list of types to parse, types not in list will be ignored. If None (default), then all object types will be parsed
    """
    suffix = ""
    indent = ""
    emphasis = ""
    obj_type = object_instance.__mro__[-2]
    link = f"https://github.com/ORNL-MDF/Myna/tree/{branch}/src/{object_instance.__mro__[0].__module__.replace('.', '/')}.py"
    depth = len(object_instance.__mro__)
    if depth == 2:
        emphasis = "**"
    if depth > 2:
        indent = "  " * (depth - 2)
    if include_types is None:
        line = f"{indent}- [{emphasis}{label}{emphasis}{suffix}]({link})\n"
    elif obj_type in include_types:
        line = f"{indent}- [{emphasis}{label}{suffix}{emphasis}]({link})\n"
    else:
        line = ""
    return line


# Parser comes from the top-level command parsing
def write_codebase_status_to_file(parser):
    """Writes available Myna components, data, files, and applications
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
    parser.add_argument(
        "--ghpages",
        dest="ghpages",
        default=False,
        action="store_true",
        help="flag to add GitHub Pages navigation bar header",
    )
    parser.add_argument(
        "--ghpages-nav-level",
        type=int,
        default=4,
        help="level to add GitHub Pages navigation bar header",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="main",
        help="git branch name to use when linking to classes",
    )

    # Parse cmd arguments
    args = parser.parse_args()
    output_file = args.output
    ghpages = args.ghpages
    nav_level = args.ghpages_nav_level
    branch = args.branch

    # Print header
    lines = []
    if ghpages:
        lines.append("---\n")
        lines.append("title: Components and Applications\n")
        lines.append("layout: default\n")
        lines.append(f"nav_order: {nav_level}\n")
        lines.append("---\n\n")
    lines.append("# Myna Components and Applications\n")
    if ghpages:
        lines.append("{: .no_toc }\n")
        lines.append("\n## Table of Contents\n{: .no_toc .text-delta }\n")
        lines.append("\n1. TOC\n{:toc}\n")
    lines.append(f"\nMyna version: {version('myna')}\n")
    lines.append(
        "\nThis page contains the list of available classes within Myna for"
        + " workflow components, input and output data, and applications.\n"
    )

    # Get all components classes
    obj = core.components
    lines.append("\n## Workflow Component Classes\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                lines.append(
                    format_class_string_to_list(
                        obj_inst,
                        key,
                        include_types=[obj.component.Component],
                        branch=branch,
                    )
                )
            except Exception:
                pass

    # Get all file classes
    obj = core.files
    lines.append("\n## Output File Classes\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                lines.append(
                    format_class_string_to_list(
                        obj_inst, key, include_types=[obj.file.File], branch=branch
                    )
                )
            except Exception:
                pass

    # Get all metadata classes
    obj = core.metadata
    lines.append("\n## Input Metadata and File Classes\n\n")
    for key in vars(obj).keys():
        if key[0] != "_":
            key_type = type(vars(obj)[key])
            obj_inst = vars(obj)[key]
            try:
                lines.append(
                    format_class_string_to_list(
                        obj_inst,
                        key,
                        include_types=[obj.data.BuildMetadata, obj.file.BuildFile],
                        branch=branch,
                    )
                )
            except Exception:
                pass

    # Get all applications
    path = os.environ["MYNA_APP_PATH"]
    basepath = os.environ["MYNA_INSTALL_PATH"]
    lines.append("\n## Applications\n\n")
    ignore_names = ["__pycache__"]
    for root, dirs, files in os.walk(path):
        root_simple = root.replace(basepath + os.path.sep, "")
        depth = len(root_simple.split(os.path.sep))
        app_name = os.path.basename(root)
        if app_name not in ignore_names:
            emphasis = ""
            indents = ""
            if depth in [2, 3]:
                root_link = root_simple.replace("\\", "/").replace("//", "/")
                print(root_link)
                link = f"https://github.com/ORNL-MDF/Myna/tree/{branch}/src/myna/{root_link}"
                if depth == 3:
                    emphasis = "**"
                elif depth > 3:
                    indents = "  " * (depth - 3)
                lines.append(f"{indents}- [{emphasis}{app_name}{emphasis}]({link})\n")

    with open(output_file, "w") as f:
        f.writelines(lines)
