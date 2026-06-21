#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest

from myna.core.utils import (
    build_part_layer_records,
    build_part_layer_dependency_index,
    load_part_layer_interface_index,
)


def test_load_part_layer_interface_index():
    settings = {
        "data": {
            "build": {
                "part_layer_interfaces": [
                    {
                        "part": "P2",
                        "layer": "100",
                        "previous_part": "P1",
                        "previous_layer": "99",
                    }
                ]
            }
        }
    }

    assert load_part_layer_interface_index(settings) == {
        ("P2", 100): ("P1", 99),
    }


def test_load_part_layer_interface_index_rejects_missing_keys():
    settings = {
        "data": {
            "build": {
                "part_layer_interfaces": [
                    {
                        "part": "P2",
                        "layer": 100,
                        "previous_part": "P1",
                    }
                ]
            }
        }
    }

    with pytest.raises(ValueError, match="missing required keys: previous_layer"):
        load_part_layer_interface_index(settings, error_prefix="thesis/test")


def test_build_part_layer_dependency_index_uses_interface_mapping():
    records_by_part = {
        "P1": [
            {"part": "P1", "layer": 99, "case_dir": "/tmp/P1/99"},
        ],
        "P2": [
            {"part": "P2", "layer": 100, "case_dir": "/tmp/P2/100"},
            {"part": "P2", "layer": 101, "case_dir": "/tmp/P2/101"},
        ],
    }
    interface_index = {("P2", 100): ("P1", 99)}

    dependency_index, record_index = build_part_layer_dependency_index(
        records_by_part,
        interface_index=interface_index,
    )

    assert dependency_index == {
        ("P1", 99): None,
        ("P2", 100): ("P1", 99),
        ("P2", 101): ("P2", 100),
    }
    assert record_index[("P2", 100)]["case_dir"] == "/tmp/P2/100"


def test_build_part_layer_records_groups_and_sorts_cases(tmp_path):
    first_case = tmp_path / "P2" / "101" / "surface"
    second_case = tmp_path / "P1" / "99" / "surface"
    third_case = tmp_path / "P2" / "100" / "surface"
    case_settings = {
        str(first_case): {
            "build": {
                "parts": {"P2": {"layer_data": {"101": {}}}},
                "build_data": {"preheat": {"value": 455.0}},
            }
        },
        str(second_case): {
            "build": {
                "parts": {"P1": {"layer_data": {"99": {}}}},
                "build_data": {"preheat": {"value": 410.0}},
            }
        },
        str(third_case): {
            "build": {
                "parts": {"P2": {"layer_data": {"100": {}}}},
                "build_data": {"preheat": {"value": 450.0}},
            }
        },
    }
    myna_files = [
        first_case / "temperature_surface.csv",
        second_case / "temperature_surface.csv",
        third_case / "temperature_surface.csv",
    ]

    records_by_part = build_part_layer_records(
        myna_files,
        lambda case_dir: case_settings[case_dir],
    )

    assert set(records_by_part) == {"P1", "P2"}
    assert [record["layer"] for record in records_by_part["P2"]] == [100, 101]
    assert records_by_part["P2"][0]["myna_file"] == myna_files[2]
    assert records_by_part["P1"][0]["preheat"] == 410.0


def test_build_part_layer_dependency_index_sorts_part_records():
    records_by_part = {
        "P2": [
            {"part": "P2", "layer": 101, "case_dir": "/tmp/P2/101"},
            {"part": "P2", "layer": 100, "case_dir": "/tmp/P2/100"},
        ],
    }

    dependency_index, _ = build_part_layer_dependency_index(records_by_part)

    assert dependency_index == {
        ("P2", 100): None,
        ("P2", 101): ("P2", 100),
    }


def test_build_part_layer_dependency_index_rejects_unknown_previous_case():
    records_by_part = {
        "P2": [
            {"part": "P2", "layer": 100},
        ],
    }
    interface_index = {("P2", 100): ("P1", 99)}

    with pytest.raises(
        ValueError,
        match="references previous-layer cases that are not configured",
    ):
        build_part_layer_dependency_index(
            records_by_part,
            interface_index=interface_index,
            error_prefix="thesis/test",
        )
