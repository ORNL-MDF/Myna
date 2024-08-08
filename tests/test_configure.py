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
import sys, os, shutil

import myna


# This test checks that all examples can be correctly configured.
def run_configure(path, example):
    parser = argparse.ArgumentParser("test")

    test_dir = os.getcwd()
    # Currently required to run from the example folder
    example_path = os.path.join(path, "../examples", example)
    os.chdir(example_path)

    # We do not want actual commandline args here
    if "--interfaces" in sys.argv:
        sys.argv.remove("--interfaces")
    # Rely heavily on defaults (only modify output to avoid local changes from test execution)
    output_dir = os.path.join(path, "tmp")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    sys.argv.extend(["--output", os.path.join(output_dir, "test.json")])
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

    # This file will be in myna/tests
    abs_path = os.path.dirname(os.path.abspath(__file__))
    for example in examples:
        run_configure(abs_path, example)

    # Cleanup files
    shutil.rmtree(os.path.join(abs_path, "tmp"))
