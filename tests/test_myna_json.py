#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os

import myna

from .example_paths import DATABASES_DIR


def test_myna_json_resolves_database_relative_scanpaths():
    db = myna.database.MynaJSON()
    db.set_path(
        os.fspath(DATABASES_DIR / "MynaJSON" / "MynaJSON_database_example.json")
    )

    scanpath = db.load(myna.core.metadata.Scanpath, part="P5", layer="51")

    assert os.path.exists(scanpath)
