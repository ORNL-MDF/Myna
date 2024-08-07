#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
import argparse
import sys, os

import myna


# This test checks that all examples can be correctly configured.
def run_configure(path):
    parser = argparse.ArgumentParser("test")

    test_dir = os.getcwd()
    # Currently required to run from the example folder
    os.chdir(path)

    sys.argv.extend(["--output", "test.json"])
    # Rely heavily on defaults (no other modified args)
    myna.core.workflow.config.main(parser)

    os.chdir(test_dir)


def test_configure():
    examples = [
        "cluster_solidification",
        "microstructure_region",
        "solidification_part",
        "temperature_part",
        "melt_pool_geometry_part",
        "openfoam_meshing",
        "solidification_region_reduced",
        "solidification_region_stl",
    ]
    for example in examples:
        path = os.path.join("examples", example)
        run_configure(path)
