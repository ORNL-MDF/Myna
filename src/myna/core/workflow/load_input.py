#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import copy
import os
import json
from collections.abc import Callable
from pathlib import Path, PurePath
from typing import Any
import yaml


PathTransform = Callable[[str, Path], str]


def validate_required_input_keys(settings):
    """Validates the settings dictionary to ensure it has the necessary keys for
    a Myna input dictionary

    Args:
        settings: (dict) input settings

    Returns:
        (dict) validated input settings
    """
    # Enforce that main keys exist
    for key in ["steps", "data", "myna"]:
        if settings.get(key) is None:
            settings[key] = {}

    return settings


def get_validated_input_filetype(filename):
    """Returns the validate input filetype ("yaml" or "json") and throws an error
    if the input type is not valid.

    Args:
        filename: (str) the name or path of the input file"""
    filetype = os.path.splitext(filename)[1].lower()
    if is_yaml_type(filetype):
        return "yaml"
    elif is_json_type(filetype):
        return "json"
    else:
        error_msg = (
            f'Unsupported input file type "{filetype}".'
            " Accepted input file formats are:"
            '\n- ".yaml" or ".myna-workspace"'
            '\n- ".json" or ".myna-workspace-json"'
        )
        raise ValueError(error_msg)


def is_yaml_type(filetype):
    """Boolean of if file_type if Myna-accepted YAML format"""
    return filetype in (".yaml", ".myna-workspace")


def is_json_type(filetype):
    """Boolean of if file_type if Myna-accepted JSON format"""
    return filetype in (".json", ".myna-workspace-json")


def _resolve_path(path_value: str, base_dir: Path) -> str:
    """Resolve a path string relative to a file's parent directory."""

    if not isinstance(path_value, str) or path_value == "":
        return path_value

    path = Path(path_value).expanduser()
    if path.is_absolute():
        return str(path.resolve(strict=False))
    return str((base_dir / path).resolve(strict=False))


def _relativize_path(path_value: str, base_dir: Path) -> str:
    """Relativize a path string against a file's parent directory."""

    if not isinstance(path_value, str) or path_value == "":
        return path_value

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        return path_value
    resolved_path = path.resolve(strict=False)
    if not _shares_path_anchor(resolved_path, base_dir):
        return str(resolved_path)
    return os.path.relpath(resolved_path, start=base_dir)


def _shares_path_anchor(path: PurePath, base_dir: PurePath) -> bool:
    """Whether two absolute paths can be safely relativized against each other."""

    if not path.is_absolute() or not base_dir.is_absolute():
        return True
    return path.anchor.casefold() == base_dir.anchor.casefold()


def _walk_file_local_paths(
    value: Any, transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to every `file_local` entry in a settings structure."""

    if isinstance(value, dict):
        for key, child in value.items():
            if key == "file_local":
                value[key] = transform(child, base_dir)
            else:
                _walk_file_local_paths(child, transform, base_dir)
    elif isinstance(value, list):
        for child in value:
            _walk_file_local_paths(child, transform, base_dir)


def _transform_data_file_local_paths(
    settings: dict[str, Any], transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to data-scoped `file_local` entries."""

    data_settings = settings.get("data", {})
    if isinstance(data_settings, dict) and data_settings:
        _walk_file_local_paths(data_settings, transform, base_dir)
        return

    # Case-local `myna_data.yaml` files store the build payload at the top level.
    build_settings = settings.get("build", {})
    if isinstance(build_settings, dict) and build_settings:
        _walk_file_local_paths(build_settings, transform, base_dir)


def _transform_output_paths(
    settings: dict[str, Any], transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to configured workflow output paths."""

    output_paths = settings.get("data", {}).get("output_paths", {})
    if isinstance(output_paths, dict):
        for step_name, paths in output_paths.items():
            if isinstance(paths, list):
                output_paths[step_name] = [transform(path, base_dir) for path in paths]


def _transform_workspace(
    settings: dict[str, Any], transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to the optional workspace path."""

    myna_settings = settings.get("myna", {})
    if isinstance(myna_settings, dict) and "workspace" in myna_settings:
        myna_settings["workspace"] = transform(myna_settings["workspace"], base_dir)


def _transform_build_path(
    settings: dict[str, Any], transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to the configured build path."""

    data_settings = settings.get("data", {})
    build_settings = data_settings.get("build", {})
    if isinstance(build_settings, dict) and "path" in build_settings:
        build_settings["path"] = transform(build_settings["path"], base_dir)


def _transform_step_runtime_paths(
    settings: dict[str, Any], transform: PathTransform, base_dir: Path
) -> None:
    """Apply a transform to step-scoped runtime path arguments."""

    for step in settings.get("steps", []):
        if not isinstance(step, dict):
            continue
        for step_settings in step.values():
            if not isinstance(step_settings, dict):
                continue
            for operation in ("configure", "execute", "postprocess"):
                operation_settings = step_settings.get(operation, {})
                if not isinstance(operation_settings, dict):
                    continue
                for key in ("docker-config", "docker_config"):
                    if key in operation_settings:
                        operation_settings[key] = transform(
                            operation_settings[key], base_dir
                        )


def resolve_input_paths(settings: dict[str, Any], filename: str) -> dict[str, Any]:
    """Resolve runtime and build paths relative to the loaded input file."""

    base_dir = Path(filename).expanduser().resolve(strict=False).parent
    _transform_build_path(settings, _resolve_path, base_dir)
    _transform_output_paths(settings, _resolve_path, base_dir)
    _transform_workspace(settings, _resolve_path, base_dir)
    _transform_data_file_local_paths(settings, _resolve_path, base_dir)
    _transform_step_runtime_paths(settings, _resolve_path, base_dir)
    return settings


def relativize_runtime_paths(settings: dict[str, Any], filename: str) -> dict[str, Any]:
    """Relativize runtime-local paths against the written file location."""

    base_dir = Path(filename).expanduser().resolve(strict=False).parent
    _transform_output_paths(settings, _relativize_path, base_dir)
    _transform_workspace(settings, _relativize_path, base_dir)
    _transform_data_file_local_paths(settings, _relativize_path, base_dir)
    _transform_step_runtime_paths(settings, _relativize_path, base_dir)
    return settings


def load_input(filename):
    """Load input file into dictionary

    Args:
        filename: path to input file (str) to load

    Returns:
        settings: dictionary of input file settings
    """

    with open(filename, "r", encoding="utf-8") as f:
        filetype = get_validated_input_filetype(filename)
        if filetype == "yaml":
            settings = yaml.safe_load(f)
        else:
            settings = json.load(f)
        settings = validate_required_input_keys(settings)
        return resolve_input_paths(settings, filename)


def write_input(settings, filename, relative_paths=False):
    """Write Myna input dictionary to file

    Args:
        settings: (dict) Myna input dictionary
        filename: (str) path to file to write
        relative_paths: (bool) write runtime-local paths relative to the file location
    """

    # Ensure that required input keys exist
    settings = validate_required_input_keys(copy.deepcopy(settings))
    if relative_paths:
        settings = relativize_runtime_paths(settings, filename)

    # Write the Myna input dictionary to a file
    with open(filename, "w", encoding="utf-8") as f:
        filetype = get_validated_input_filetype(filename)
        if filetype == "yaml":
            yaml.safe_dump(
                settings, f, sort_keys=False, default_flow_style=None, indent=2
            )
        else:
            json.dump(settings, f, sort_keys=False, indent=2)
