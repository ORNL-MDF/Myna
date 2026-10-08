#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Tests for file values passed to database sync."""

import polars as pl

from myna.core.files.file_temperature import FileTemperature


def test_spatial_sync_locator_preserves_x_y_order(tmp_path):
    output = tmp_path / "temperature.csv"
    pl.DataFrame(
        {
            "x (m)": [1.0, 2.0],
            "y (m)": [10.0, 20.0],
            "T (K)": [300.0, 400.0],
        }
    ).write_csv(output)

    locator, values, value_names, _ = FileTemperature(output).get_values_for_sync(
        mode="spatial_2d"
    )

    assert locator[0].tolist() == [1.0, 2.0]
    assert locator[1].tolist() == [10.0, 20.0]
    assert value_names == ["t"]
    assert values[0].tolist() == [300.0, 400.0]
