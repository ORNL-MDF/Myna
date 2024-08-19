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

    # Currently required to run from the example folder
    test_dir = os.getcwd()
    example_path = os.path.join(path, "../examples", example)
    os.chdir(example_path)

    # Rely heavily on defaults (modify output to avoid local changes from test)
    output_dir = os.path.join(example_path, "tmp")
    output_file = os.path.join(output_dir, "test.json")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    sys.argv = ["test", "--output", output_file]
    myna.core.workflow.config.main(parser)

    # Check if output file was generated
    assert os.path.exists(output_file)

    # Cleanup
    shutil.rmtree(output_dir)
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
