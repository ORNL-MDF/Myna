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
from myna.core.utils import nested_set, nested_get
from myna.core import components
from myna.core import metadata
from myna import database
from importlib.metadata import version
import datetime
import getpass
from git import Repo, InvalidGitRepositoryError


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

    # Set environmental variable for input file location
    os.environ["MYNA_INPUT"] = os.path.abspath(input_file)
    os.environ["MYNA_CONFIG_INPUT"] = os.path.abspath(
        input_file
    )  # MYNA_CONFIG_INPUT will be deprecated in future versions

    # Set output file
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

    # Write out initial Myna configuration metadata
    nested_set(settings, ["myna", "version"], version("myna"))
    user_name = ""
    try:
        user_name = getpass.getuser()  # may fail when run by service manager, e.g., CI
    except:
        pass
    configure_dict = {
        "datetime-start": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user-login": user_name,
        "input-file": os.path.abspath(input_file),
        "output-file": os.path.abspath(output_file),
    }
    nested_set(settings, ["myna", "configure"], configure_dict)

    # Check if necessary paths exist and create if not
    nested_get(settings, ["data", "output_paths"], {})
    nested_get(settings, ["data", "build", "parts"], {})
    nested_get(settings, ["data", "build", "build_regions"], {})

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

    # Get part names at build level and build region levels
    all_parts = list(settings["data"]["build"].get("parts", {}).keys())
    build_regions = nested_get(settings, ["data", "build", "build_regions"], {})
    for build_region in build_regions.keys():
        build_region_parts = build_regions[build_region].get("partlist", [])
        all_parts.extend(build_region_parts)
    all_parts = list(set(all_parts))

    # Check that some amount of parts were specified
    if len(all_parts) < 1:
        print(f"ERROR: No parts specified in {input_file}")
        raise ValueError

    # Get list of all layers in build parts and build_region parts
    all_layers = []
    for part in nested_get(settings, ["data", "build", "parts"], []):
        part_layers = nested_get(
            settings, ["data", "build", "parts", part, "layers"], []
        )
        all_layers.extend(part_layers)
    for build_region in nested_get(settings, ["data", "build", "build_regions"], []):
        build_region_layers = nested_get(
            settings, ["data", "build", "build_regions", build_region, "layerlist"], []
        )
        all_layers.extend(build_region_layers)
    all_layers = list(set(all_layers))

    # Determine which data needs to be added based on component class requirements
    step_obj_prev = None
    for i, step in enumerate(settings["steps"]):

        # Get the step component class name and class object
        step_name = [x for x in step.keys()][0]
        component_class_name = step[step_name]["class"]
        print(f"\n- Configuring step {step_name} ({component_class_name})")
        step_obj = components.return_step_class(component_class_name)
        step_obj.name = step_name
        step_obj.component_class = component_class_name
        step_obj.component_application = step[step_name]["application"]

        # Raise warning if there is an input requirement and it is the first step
        if (i == 0) and step_obj.input_requirement is not None:
            print(f"Warning: Step {step_name} requires input, but is the first step.")

        # Set the input and output templates
        step_obj.input_template = step.get(step_name).get("input_template")
        if (step_obj.input_template == "") or (step_obj.input_template is None):
            if step_obj_prev is not None:
                step_obj.input_template = step_obj_prev.output_template
        step_obj.output_template = step.get(step_name).get("output_template")

        # Get any CUI labels for the build
        try:
            settings["data"]["build"]["cui-markings"] = datatype.get_cui_info()
        except NotImplementedError:
            settings["data"]["build"]["cui-markings"] = "N/A"
            pass

        # Get the data requirements associated with that class
        for data_req in step_obj.data_requirements:

            # For each data requirements, lookup the corresponding data object
            data_class_name = metadata.return_data_class_name(data_req)
            constructor = vars(metadata)[data_class_name]

            # Construct the relevant data object
            if constructor.__base__ == metadata.BuildMetadata:
                nested_keys = ["data", "build", "build_data"]
                nested_get(settings, nested_keys, {})
                data_obj = constructor(datatype)
                datum = {"value": data_obj.value, "unit": data_obj.unit}
                nested_keys.append(data_req)
                nested_set(settings, nested_keys, datum)
            elif constructor.__base__ == metadata.PartMetadata:
                if "build_region" in step_obj.types:
                    nested_keys = ["data", "build", "build_regions"]
                    build_regions = list(nested_get(settings, nested_keys, {}).keys())
                    for build_region in build_regions:
                        nested_keys_buildregion = nested_keys + [
                            build_region,
                            "partlist",
                        ]
                        parts = nested_get(settings, nested_keys_buildregion, [])
                        for part in parts:
                            data_obj = constructor(datatype, str(part))
                            datum = {"value": data_obj.value, "unit": data_obj.unit}
                            nested_partkeys = nested_keys + [
                                build_region,
                                "parts",
                                part,
                                data_req,
                            ]
                            nested_set(settings, nested_partkeys, datum)
                else:
                    nested_keys = ["data", "build", "parts"]
                    parts = nested_get(settings, nested_keys, {})
                    for part in parts.keys():
                        data_obj = constructor(datatype, part)
                        datum = {"value": data_obj.value, "unit": data_obj.unit}
                        nested_partkeys = nested_keys + [part, data_req]
                        nested_set(settings, nested_partkeys, datum)

            # Construct the relevant file object
            elif constructor.__base__ == metadata.BuildFile:
                data_obj = constructor(datatype)
                data_obj.copy_file(overwrite=overwrite)
                datum = {
                    "file_local": data_obj.file_local,
                    "file_database": data_obj.file_database,
                }
                nested_set(settings, ["data", "build", data_req], datum)
            elif constructor.__base__ == metadata.BuildLayerPartsetFile:
                nested_keys = ["data", "build", "layer_data"]
                nested_get(settings, nested_keys, {})
                for layer in all_layers:
                    data_obj = constructor(datatype, all_parts, layer)
                    data_obj.copy_file()
                    datum = {
                        "file_local": data_obj.file_local,
                        "file_database": data_obj.file_database,
                    }
                    nested_layerkey = nested_keys + [f"{layer}", data_req]
                    nested_set(settings, nested_layerkey, datum)
            elif constructor.__base__ == metadata.PartFile:

                def set_partfile_entry(datatype, part, input_dict, nested_keys):
                    data_obj = constructor(datatype, str(part))
                    data_obj.copy_file(overwrite=overwrite)
                    partfile_dict = {
                        "file_local": data_obj.file_local,
                        "file_database": data_obj.file_database,
                    }
                    nested_set(input_dict, nested_keys, partfile_dict)

                if "build_region" in step_obj.types:
                    nested_keys = ["data", "build", "build_regions"]
                    for build_region in nested_get(settings, nested_keys, {}):
                        nested_buildregion_keys = nested_keys + [build_region, "parts"]
                        parts = nested_get(settings, nested_buildregion_keys, {})
                        for part in parts.keys():
                            nested_partkeys = nested_buildregion_keys + [part, data_req]
                            set_partfile_entry(
                                datatype, part, settings, nested_partkeys
                            )
                else:
                    nested_keys = ["data", "build", "parts"]
                    parts = nested_get(settings, nested_keys, {})
                    for part in parts.keys():
                        nested_partkeys = nested_keys + [part, data_req]
                        set_partfile_entry(datatype, part, settings, nested_partkeys)

            elif constructor.__base__ == metadata.LayerFile:

                def set_layerfile_entry(datatype, part, layer, input_dict, nested_keys):
                    data_obj = constructor(datatype, part, layer)
                    data_obj.copy_file(overwrite=overwrite)
                    layerfile_dict = {
                        "file_local": data_obj.file_local,
                        "file_database": data_obj.file_database,
                    }
                    nested_set(input_dict, nested_keys, layerfile_dict)

                if "build_region" in step_obj.types:
                    nested_keys = ["data", "build", "build_regions"]
                    builds_regions = list(nested_get(settings, nested_keys, {}).keys())
                    for build_region in builds_regions:
                        parts = nested_get(
                            settings, nested_keys + [build_region, "partlist"], []
                        )
                        for part in parts:
                            part_layers = nested_get(
                                settings, nested_keys + [build_region, "layerlist"], []
                            )
                            for l in part_layers:
                                layer = f"{l}"
                                nested_layerkeys = nested_keys + [
                                    build_region,
                                    "parts",
                                    part,
                                    "layer_data",
                                    layer,
                                    data_req,
                                ]
                                set_layerfile_entry(
                                    datatype, part, layer, settings, nested_layerkeys
                                )
                else:
                    parts = nested_get(settings, ["data", "build", "parts"], {})
                    for part in parts.keys():
                        # Check for layers in part dictionary
                        part_layers = nested_get(parts, [part, "layers"], [])
                        for l in part_layers:
                            layer = f"{l}"
                            nested_keys = [
                                "data",
                                "build",
                                "parts",
                                part,
                                "layer_data",
                                layer,
                                data_req,
                            ]
                            set_layerfile_entry(
                                datatype, part, layer, settings, nested_keys
                            )

                        # Check for layers in region dictionary
                        regions = nested_get(parts, [part, "regions"], {})
                        for region in regions.keys():
                            region_layers = nested_get(
                                parts, [part, "regions", region, "layers"], []
                            )
                            for l in region_layers:
                                layer = f"{l}"
                                nested_keys = [
                                    "data",
                                    "build",
                                    "parts",
                                    part,
                                    "regions",
                                    region,
                                    "layer_data",
                                    layer,
                                    data_req,
                                ]
                                set_layerfile_entry(
                                    datatype, part, layer, settings, nested_keys
                                )

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
            if "build_region" in step_obj.types:
                data_dict_case["build"].pop("parts", None)
                build_region = build_struct[2]
                build_region_parts = data_dict_case["build"]["build_regions"][
                    build_region
                ]["parts"]
                keys = list(data_dict_case["build"]["build_regions"].keys())
                for key in keys:
                    if key != build_region:
                        data_dict_case["build"]["build_regions"].pop(key, None)
                    else:
                        if "part" in step_obj.types:
                            nested_buildregion_keys = [
                                "build",
                                "build_regions",
                                build_region,
                                "parts",
                            ]
                            build_region_parts = nested_get(
                                data_dict_case, nested_buildregion_keys, {}
                            )
                            for part in build_region_parts.keys():
                                if "layer" in step_obj.types:
                                    layer = build_struct[3]
                                    nested_layerdata_keys = nested_buildregion_keys + [
                                        part,
                                        "layer_data",
                                    ]
                                    part_layer_data = nested_get(
                                        data_dict_case, nested_layerdata_keys, {}
                                    )
                                    for key in part_layer_data.keys():
                                        if int(key) != int(layer):
                                            data_dict_case["build"]["parts"][part][
                                                "layer_data"
                                            ].pop(key, None)
                                    nested_layerlist_keys = nested_buildregion_keys + [
                                        part,
                                        "layerlist",
                                    ]
                                    nested_set(
                                        data_dict_case,
                                        nested_layerlist_keys,
                                        [int(layer)],
                                    )
            elif "part" in step_obj.types:
                part = build_struct[2]
                keys = list(data_dict_case["build"]["parts"].keys())
                for key in keys:
                    if key != part:
                        data_dict_case["build"]["parts"].pop(key, None)
                if "region" in step_obj.types:
                    region = build_struct[3]
                    keys = list(
                        data_dict_case["build"]["parts"][part]["regions"].keys()
                    )
                    for key in keys:
                        if key != region:
                            data_dict_case["build"]["parts"][part]["regions"].pop(
                                key, None
                            )
                    if "layer" in step_obj.types:
                        layer = build_struct[4]
                        keys = list(
                            data_dict_case["build"]["parts"][part]["regions"][region][
                                "layer_data"
                            ].keys()
                        )
                        for key in keys:
                            if key != layer:
                                data_dict_case["build"]["parts"][part]["regions"][
                                    region
                                ]["layer_data"].pop(key, None)
            else:
                if "layer" in step_obj.types:
                    layer = build_struct[3]
                    keys = list(
                        nested_get(
                            data_dict_case, ["build", "parts", part, "layer_data"], {}
                        ).keys()
                    )
                    for key in keys:
                        if key != layer:
                            data_dict_case["build"]["parts"][part]["layer_data"].pop(
                                key, None
                            )

            # Copy basic information about the Myna workflow
            data_dict_case["myna"] = nested_get(settings, ["myna"])

            # Add information about the git repository (if present)
            try:
                repo_path = os.path.abspath(
                    os.path.join(os.environ["MYNA_INSTALL_PATH"], "..", "..")
                )
                repo = Repo(repo_path)
                nested_set(
                    data_dict_case, ["myna", "git", "commit"], repo.head.commit.hexsha
                )
                nested_set(
                    data_dict_case, ["myna", "git", "branch"], str(repo.active_branch)
                )
                nested_set(
                    data_dict_case, ["myna", "git", "origin"], repo.remotes.origin.url
                )
                is_dirty = repo.is_dirty()
                nested_set(data_dict_case, ["myna", "git", "is_dirty"], is_dirty)
                if is_dirty:
                    dirty_files = []
                    untracked_files = []
                    diffs = repo.head.commit.diff(None)
                    for d in diffs:
                        dirty_files.append(str(d.a_path))
                    for untracked in repo.untracked_files:
                        untracked_files.append(untracked)
                    nested_set(
                        data_dict_case, ["myna", "git", "dirty_files"], dirty_files
                    )
                    nested_set(
                        data_dict_case,
                        ["myna", "git", "untracked_files"],
                        untracked_files,
                    )
                nested_set(
                    settings,
                    ["myna", "git"],
                    nested_get(data_dict_case, ["myna", "git"]),
                )
            except (InvalidGitRepositoryError, TypeError):
                # InvalidGitRepositoryError: Not a Git repository
                # TypeError: HEAD is detached
                pass

            # Set configure data
            nested_set(
                data_dict_case,
                ["myna", "configure"],
                nested_get(settings, ["myna", "configure"]),
            )

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
            nested_set(settings, ["data", "output_paths", step_name], files)

        # Save step as previous step to get input files for next step
        step_obj_prev = step_obj

        print(f'  > "{step_name}" complete\n')

    # Write out configuration metadata
    nested_set(
        settings,
        ["myna", "configure", "datetime-end"],
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    with open(output_file, "w") as f:
        yaml.dump(settings, f, sort_keys=False, default_flow_style=None)
