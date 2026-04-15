#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil

import myna
import myna.database

from .example_paths import CASES_DIR, DATABASES_DIR


# This test is intended to ensure the database parsing is working
def test_database_PeregrineHDF5(tmp_path):
    db = myna.database.PeregrineHDF5()
    database_copy_dir = tmp_path / "PeregrineHDF5"
    database_copy_dir.mkdir()
    database_copy = database_copy_dir / "minimal.hdf5"
    shutil.copyfile(DATABASES_DIR / "PeregrineHDF5" / "minimal.hdf5", database_copy)
    db.set_path(os.fspath(database_copy))
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
    db.set_path(os.fspath(DATABASES_DIR))
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


def test_database_pelican(tmp_path):
    """Test if the Pelican database class is working for the expected metadata types"""

    database_copy = tmp_path / "Pelican"
    shutil.copytree(DATABASES_DIR / "Pelican", database_copy)

    db = myna.database.Pelican()
    db.set_path(os.fspath(database_copy))
    test_metadata_types = [
        myna.core.metadata.Material,
        myna.core.metadata.LayerThickness,
        myna.core.metadata.Preheat,
        myna.core.metadata.LaserPower,
        myna.core.metadata.SpotSize,
        myna.core.metadata.Scanpath,
    ]

    for metadata_type in test_metadata_types:
        os.environ["MYNA_INPUT"] = os.fspath(
            CASES_DIR / "solidification_part_pelican" / "input.yaml"
        )
        assert db.load(metadata_type, part="P0", layer=0) is not None
