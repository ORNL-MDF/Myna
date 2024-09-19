#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines `myna config` functionality"""

import os
import yaml
import copy
from myna.core.workflow.load_input import load_input
from myna.core import components
from myna.core import metadata
from myna import database
from importlib.metadata import version
import datetime
import getpass


# Parser comes from the top-level command parsing
def parse(parser):
    """Main function for configuring a myna case from the command line"""

    parser.add_argument(
        "--input",
        default="input.yaml",
        type=str,
        help="path to the desired input file to run"
        + ", for example: "
        + "--input demo.yaml",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="path to the desired output file to write"
        + ", for example: "
        + "--output demo.yaml",
    )
    parser.add_argument(
        "--avail",
        default=False,
        action="store_true",
        help="switch to show all available data files, but will"
        + "not update input file data values",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        default=False,
        action="store_true",
        help="(flag) overwrite existing files in Myna resources, default = False",
    )

    # Parse cmd arguments
    args = parser.parse_args()
    config(args.input, args.output, args.avail, args.overwrite)


def config(input_file, output_file=None, show_avail=False, overwrite=False):
    """Configure a myna workflow based on an input file

    Args:
      input_file: path to Myna input file
      output_file: path to write configured input file, if None set input_file
      show_avail: only shows available data files, but does not copy
      overwrite: flag to overwrite existing files in Myna resources"""

    if output_file is None:
        output_file = input_file

    # Load input file
    settings = load_input(input_file)

    # Check build directory contains the expected metadata folder
    build_path = settings["data"]["build"]["path"]
    datatype = database.return_datatype_class(settings["data"]["build"]["datatype"])
    datatype.set_path(build_path)
    if not datatype.exists():
        print(f"ERROR: Could not find valid {datatype} in" + f" {build_path}")
        raise FileNotFoundError

    # Get part names
    parts = settings["data"]["build"]["parts"]
    all_parts = list(parts.keys())
    if len(parts) < 1:
        print(f"ERROR: No data/parts specified in {input_file}")
        raise ValueError

    # Get list of all layers in build
    all_layers = []
    for part in parts.keys():
        part_layers = parts[part].get("layers")
        if part_layers is not None:
            all_layers.extend(part_layers)
    all_layers = list(set(all_layers))

    # Check if {"data": {"output_paths":}} key  and create if not
    value = settings["data"].get("output_paths")
    if value is None:
        settings["data"]["output_paths"] = {}

    # If specified, get available data. Otherwise extract necessary data
    if show_avail:
        print("Available metadata:\n-------------------------")
        last_path = ""
        for path, dirs, files in os.walk(datatype.path):
            for f in files:
                if len(dirs) == 0:
                    if last_path is not path:
                        print(path)
                    print("    " * (len(dirs) + 1), f)
                    last_path = path
        return

    # Determine which data needs to be added based on component class requirements
    step_obj_prev = None
    for i, step in enumerate(settings["steps"]):
        # Get the step component class name
        step_name = [x for x in step.keys()][0]
        component_class_name = step[step_name]["class"]
        print(f"\n- Configuring step {step_name} ({component_class_name})")
        step_obj = components.return_step_class(component_class_name)
        step_obj.name = step_name
        step_obj.component_class = component_class_name
        step_obj.component_application = step[step_name]["application"]

        # Raise error if there is an input requirement and it is the first step
        if (i == 0) and step_obj.input_requirement is not None:
            print(f"Warning: Step {step_name} requires input, but is the first step.")

        # Set the input and output templates
        step_obj.input_template = step.get(step_name).get("input_template")
        if (step_obj.input_template == "") or (step_obj.input_template is None):
            if step_obj_prev is not None:
                step_obj.input_template = step_obj_prev.output_template
        step_obj.output_template = step.get(step_name).get("output_template")

        # Get the data requirements associated with that class
        for data_req in step_obj.data_requirements:
            # For each data requirements, lookup the corresponding data object
            data_class_name = metadata.return_data_class_name(data_req)
            constructor = vars(metadata)[data_class_name]

            # Construct the relevant data object
            if constructor.__base__ == metadata.BuildMetadata:
                if settings["data"]["build"].get("build_data") is None:
                    settings["data"]["build"]["build_data"] = {}
                data_obj = constructor(datatype)
                datum = {"value": data_obj.value, "unit": data_obj.unit}
                settings["data"]["build"]["build_data"][data_req] = datum
            elif constructor.__base__ == metadata.PartMetadata:
                for part in parts.keys():
                    data_obj = constructor(datatype, part)
                    datum = {"value": data_obj.value, "unit": data_obj.unit}
                    settings["data"]["build"]["parts"][part][data_req] = datum

            # Construct the relevant file object
            elif constructor.__base__ == metadata.BuildFile:
                data_obj = constructor(datatype)
                data_obj.copy_file(overwrite=overwrite)
                datum = {
                    "file_local": data_obj.file_local,
                    "file_database": data_obj.file_database,
                }
                settings["data"]["build"][data_req] = datum
            elif constructor.__base__ == metadata.BuildLayerPartsetFile:
                for layer in all_layers:
                    data_obj = constructor(datatype, all_parts, layer)
                    data_obj.copy_file()
                    datum = {
                        "file_local": data_obj.file_local,
                        "file_database": data_obj.file_database,
                    }
                    if settings["data"]["build"].get("layer_data") is None:
                        settings["data"]["build"]["layer_data"] = {}
                    if settings["data"]["build"]["layer_data"].get(f"{layer}") is None:
                        settings["data"]["build"]["layer_data"][f"{layer}"] = {}
                    settings["data"]["build"]["layer_data"][f"{layer}"][
                        data_req
                    ] = datum
            elif constructor.__base__ == metadata.PartFile:
                for part in parts.keys():
                    data_obj = constructor(datatype, part)
                    data_obj.copy_file(overwrite=overwrite)
                    datum = {
                        "file_local": data_obj.file_local,
                        "file_database": data_obj.file_database,
                    }
                    settings["data"]["build"]["parts"][part][data_req] = datum
            elif constructor.__base__ == metadata.LayerFile:
                for part in parts.keys():
                    # Check for layers in part dictionary
                    part_layers = parts[part].get("layers")
                    if part_layers is not None:
                        for l in part_layers:
                            layer = f"{l}"
                            if (
                                settings["data"]["build"]["parts"][part].get(
                                    "layer_data"
                                )
                                is None
                            ):
                                settings["data"]["build"]["parts"][part][
                                    "layer_data"
                                ] = {}
                            if (
                                settings["data"]["build"]["parts"][part][
                                    "layer_data"
                                ].get(layer)
                                is None
                            ):
                                settings["data"]["build"]["parts"][part]["layer_data"][
                                    layer
                                ] = {}
                            data_obj = constructor(datatype, part, layer)
                            data_obj.copy_file(overwrite=overwrite)
                            datum = {
                                "file_local": data_obj.file_local,
                                "file_database": data_obj.file_database,
                            }
                            settings["data"]["build"]["parts"][part]["layer_data"][
                                layer
                            ][data_req] = datum

                    # Check for layers in region dictionary
                    regions = parts[part].get("regions")
                    if regions is not None:
                        for region in regions:
                            region_layers = parts[part]["regions"][region].get("layers")
                            if region_layers is not None:
                                for l in region_layers:
                                    layer = f"{l}"
                                    if (
                                        settings["data"]["build"]["parts"][part][
                                            "regions"
                                        ][region].get("layer_data")
                                        is None
                                    ):
                                        settings["data"]["build"]["parts"][part][
                                            "regions"
                                        ][region]["layer_data"] = {}
                                    if (
                                        settings["data"]["build"]["parts"][part][
                                            "regions"
                                        ][region]["layer_data"].get(layer)
                                        is None
                                    ):
                                        settings["data"]["build"]["parts"][part][
                                            "regions"
                                        ][region]["layer_data"][layer] = {}
                                    data_obj = constructor(datatype, part, layer)
                                    data_obj.copy_file(overwrite=overwrite)
                                    datum = {
                                        "file_local": data_obj.file_local,
                                        "file_database": data_obj.file_database,
                                    }
                                    settings["data"]["build"]["parts"][part]["regions"][
                                        region
                                    ]["layer_data"][layer][data_req] = datum

        # Save data to step object
        step_obj.apply_settings(
            step[step_name], settings.get("data"), settings.get("myna")
        )

        # Make needed directories and copy data dict to each case directory
        case_dirs = step_obj.get_files_from_template("")
        for case_dir in case_dirs:
            # Set up case directory if it doesn't exist
            if not os.path.exists(case_dir):
                os.makedirs(case_dir)

            # Select only relevant build, part, and layer information
            data_dict_case = {"build": {}}
            data_dict_case["build"] = copy.deepcopy(settings["data"]["build"])
            base_path = os.path.abspath(os.path.dirname(input_file))
            build_struct = (
                os.path.abspath(case_dir).replace(base_path, "").split(os.sep)
            )
            if "part" in step_obj.types:
                part = build_struct[2]
                keys = list(data_dict_case["build"]["parts"].keys())
                for key in keys:
                    if key != part:
                        data_dict_case["build"]["parts"].pop(key, None)
            if "region" in step_obj.types:
                region = build_struct[3]
                keys = list(data_dict_case["build"]["parts"][part]["regions"].keys())
                for key in keys:
                    if key != region:
                        data_dict_case["build"]["parts"][part]["regions"].pop(key, None)
                if "layer" in step_obj.types:
                    layer = build_struct[4]
                    keys = list(
                        data_dict_case["build"]["parts"][part]["regions"][region][
                            "layer_data"
                        ].keys()
                    )
                    for key in keys:
                        if key != layer:
                            data_dict_case["build"]["parts"][part]["regions"][region][
                                "layer_data"
                            ].pop(key, None)
            else:
                if "layer" in step_obj.types:
                    layer = build_struct[3]
                    keys = list(
                        data_dict_case["build"]["parts"][part]["layer_data"].keys()
                    )
                    for key in keys:
                        if key != layer:
                            data_dict_case["build"]["parts"][part]["layer_data"].pop(
                                key, None
                            )

            # Add basic information about the Myna workflow
            data_dict_case["myna"] = {}
            data_dict_case["myna"]["version"] = version("myna")
            data_dict_case["myna"]["input"] = os.path.abspath(input_file)

            # Write data to case directory
            with open(os.path.join(case_dir, "myna_data.yaml"), "w") as f:
                yaml.dump(data_dict_case, f, sort_keys=False, default_flow_style=None)

        # Show the inputs associated with the step
        if step_obj.input_requirement is not None:
            print(f'  > Expecting input for step "{step_name}":')
            if step_obj_prev is not None:
                files, exists, valid = step_obj.get_input_files(step_obj_prev)
                if len(files) > 0:
                    for f, e, v in zip(files, exists, valid):
                        print(f"    - {f} (exists = {e}, valid = {v})")

        # Set the outputs associated with the step
        if step_obj.output_requirement is not None:
            print(f'  > Expecting output for step "{step_name}":')
            step_obj.apply_settings(
                step[step_name], settings.get("data"), settings.get("myna")
            )
            files, exists, valid = step_obj.get_output_files()
            if len(files) > 0:
                for f, e, v in zip(files, exists, valid):
                    print(f"    - {f} (exists = {e}, valid = {v})")
            settings["data"]["output_paths"][step_name] = files

        # Save step as previous step to get input files for next step
        step_obj_prev = step_obj

        print(f'  > "{step_name}" complete\n')

    # Write out configuration metadata
    if settings.get("myna") is None:
        settings["myna"] = {}
    user_name = ""
    try:
        user_name = getpass.getuser()  # may fail when run by service manager, e.g., CI
    except:
        pass
    settings["myna"]["configure"] = {
        "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user-login": user_name,
    }

    with open(output_file, "w") as f:
        yaml.dump(settings, f, sort_keys=False, default_flow_style=None)
