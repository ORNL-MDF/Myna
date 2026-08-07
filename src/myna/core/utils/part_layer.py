#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Utilities for build part/layer workflow metadata."""

import os
import re


def _format_error(error_prefix, message):
    """Format an error message with an optional caller-specific prefix."""
    if error_prefix:
        return f"{error_prefix}: {message}"
    return message


def get_input_build_settings(settings):
    """Return build settings from a workflow or case-local Myna input."""
    build_settings = settings.get("data", {}).get("build")
    if isinstance(build_settings, dict):
        return build_settings

    build_settings = settings.get("build")
    if isinstance(build_settings, dict):
        return build_settings

    return {}


def normalize_layer_identifier(layer):
    """Normalize a case layer identifier into an integer layer number."""
    if isinstance(layer, int):
        return int(layer)
    if isinstance(layer, float) and layer.is_integer():
        return int(layer)
    layer_str = str(layer)
    try:
        return int(layer_str)
    except ValueError:
        matches = re.findall(r"\d+", layer_str)
        if len(matches) == 1:
            return int(matches[0])
    raise ValueError(f"Could not parse a numeric layer identifier from {layer!r}")


def format_part_layer_key(case_key):
    """Format a normalized `(part, layer)` key for user-facing messages."""
    part, layer = case_key
    return f"{part} layer {layer}"


def load_part_layer_interface_index(settings, error_prefix=""):
    """Load optional cross-part serial heat mappings from a Myna input."""
    build_settings = get_input_build_settings(settings)
    raw_interfaces = build_settings.get("part_layer_interfaces", [])
    if raw_interfaces is None:
        return {}
    if not isinstance(raw_interfaces, list):
        raise ValueError(
            _format_error(
                error_prefix,
                "`data.build.part_layer_interfaces` must be a list of "
                "part/layer interface mappings.",
            )
        )

    interface_index = {}
    required_keys = {"part", "layer", "previous_part", "previous_layer"}
    for index, raw_interface in enumerate(raw_interfaces):
        if not isinstance(raw_interface, dict):
            raise ValueError(
                _format_error(
                    error_prefix,
                    f"Interface mapping at index {index} must be a dictionary.",
                )
            )

        missing_keys = required_keys - set(raw_interface.keys())
        if missing_keys:
            missing_key_list = ", ".join(sorted(missing_keys))
            raise ValueError(
                _format_error(
                    error_prefix,
                    f"Interface mapping at index {index} is missing required keys: "
                    f"{missing_key_list}.",
                )
            )

        case_key = (
            str(raw_interface["part"]),
            normalize_layer_identifier(raw_interface["layer"]),
        )
        previous_key = (
            str(raw_interface["previous_part"]),
            normalize_layer_identifier(raw_interface["previous_layer"]),
        )
        if case_key == previous_key:
            raise ValueError(
                _format_error(
                    error_prefix,
                    f"Interface mapping for {format_part_layer_key(case_key)} may not "
                    "point to itself.",
                )
            )
        if case_key in interface_index:
            raise ValueError(
                _format_error(
                    error_prefix,
                    "Duplicate interface mapping specified for "
                    f"{format_part_layer_key(case_key)}.",
                )
            )
        interface_index[case_key] = previous_key

    return interface_index


def get_single_part_layer_settings(settings, error_prefix=""):
    """Return the single configured part/layer payload for one case input."""
    build_settings = get_input_build_settings(settings)
    try:
        part, part_settings = next(iter(build_settings["parts"].items()))
        layer, layer_settings = next(iter(part_settings["layer_data"].items()))
    except KeyError as exc:
        raise KeyError(
            _format_error(
                error_prefix,
                'Expected case settings to contain `build.parts[part]["layer_data"]`.',
            )
        ) from exc
    except StopIteration as exc:
        raise ValueError(
            _format_error(
                error_prefix,
                "Expected at least one configured part and layer.",
            )
        ) from exc
    return part, layer, part_settings, layer_settings


def build_part_layer_records(myna_files, load_case_settings, error_prefix=""):
    """Group case records by part using normalized layer identifiers."""
    records_by_part = {}
    for myna_file in myna_files:
        case_dir = os.path.dirname(os.fspath(myna_file))
        settings = load_case_settings(case_dir)
        build_settings = get_input_build_settings(settings)
        part, layer, _, _ = get_single_part_layer_settings(
            settings,
            error_prefix=error_prefix,
        )
        try:
            preheat = build_settings["build_data"]["preheat"]["value"]
        except KeyError as exc:
            raise KeyError(
                _format_error(
                    error_prefix,
                    "Expected case settings to include `build.build_data.preheat.value`.",
                )
            ) from exc
        record = {
            "part": part,
            "layer": normalize_layer_identifier(layer),
            "case_dir": case_dir,
            "myna_file": myna_file,
            "preheat": preheat,
        }
        records_by_part.setdefault(part, []).append(record)

    for records in records_by_part.values():
        records.sort(key=lambda record: record["layer"])
    return records_by_part


def build_part_layer_record_index(records_by_part, error_prefix=""):
    """Index case records by normalized `(part, layer)`."""
    record_index = {}
    for records in records_by_part.values():
        for record in records:
            try:
                case_key = (record["part"], record["layer"])
            except KeyError as exc:
                raise KeyError(
                    _format_error(
                        error_prefix,
                        'Expected each part/layer record to contain "part" and '
                        '"layer" entries.',
                    )
                ) from exc
            if case_key in record_index:
                raise ValueError(
                    _format_error(
                        error_prefix,
                        "Duplicate case configured for "
                        f"{format_part_layer_key(case_key)}.",
                    )
                )
            record_index[case_key] = record
    return record_index


def build_part_layer_dependency_index(
    records_by_part, interface_index=None, error_prefix=""
):
    """Resolve the previous-layer dependency for each configured case."""
    interface_index = {} if interface_index is None else interface_index
    record_index = build_part_layer_record_index(
        records_by_part,
        error_prefix=error_prefix,
    )

    missing_cases = sorted(set(interface_index) - set(record_index))
    if missing_cases:
        missing_case_list = ", ".join(
            format_part_layer_key(case_key) for case_key in missing_cases
        )
        raise ValueError(
            _format_error(
                error_prefix,
                "`data.build.part_layer_interfaces` targets cases that are not "
                f"configured for this step: {missing_case_list}.",
            )
        )

    missing_previous_cases = sorted(set(interface_index.values()) - set(record_index))
    if missing_previous_cases:
        missing_previous_case_list = ", ".join(
            format_part_layer_key(case_key) for case_key in missing_previous_cases
        )
        raise ValueError(
            _format_error(
                error_prefix,
                "`data.build.part_layer_interfaces` references previous-layer "
                f"cases that are not configured for this step: "
                f"{missing_previous_case_list}.",
            )
        )

    dependency_index = {}
    for records in records_by_part.values():
        sorted_records = sorted(records, key=lambda record: record["layer"])
        previous_key = None
        for record in sorted_records:
            case_key = (record["part"], record["layer"])
            dependency_index[case_key] = previous_key
            previous_key = case_key

    dependency_index.update(interface_index)
    return dependency_index, record_index
