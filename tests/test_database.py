#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
from importlib.metadata import version
import os

import myna
import myna.database


# This test is intended to ensure the database parsing is working
def test_database_PeregrineHDF5():

    db = myna.database.PeregrineHDF5()
    path = os.path.dirname(os.path.abspath(__file__))
    db.set_path(os.path.join(path, "..", "examples", "PeregrineHDF5", "minimal.hdf5"))
    test_metadata_types = [
        myna.core.metadata.LaserPower,
        myna.core.metadata.LayerThickness,
        myna.core.metadata.Material,
        myna.core.metadata.Preheat,
        myna.core.metadata.SpotSize,
        myna.core.metadata.Scanpath,
    ]

    for metadata_type in test_metadata_types:
        assert db.load(metadata_type, part="P1", layer=0) is not None


# This test is intended to ensure the database parsing is working
def test_database_Peregrine():

    db = myna.database.PeregrineDB()
    path = os.path.dirname(os.path.abspath(__file__))
    db.set_path(os.path.join(path, "..", "examples"))
    test_metadata_types = [
        myna.core.metadata.LaserPower,
        myna.core.metadata.LayerThickness,
        myna.core.metadata.Material,
        myna.core.metadata.Preheat,
        myna.core.metadata.STL,
        myna.core.metadata.SpotSize,
        myna.core.metadata.Scanpath,
    ]

    for metadata_type in test_metadata_types:
        assert db.load(metadata_type, part="P5", layer=50) is not None
