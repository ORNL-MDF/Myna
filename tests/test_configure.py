#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import argparse
import sys
import os
import shutil

import myna

from .example_paths import CASES_DIR


# This test checks that all examples can be correctly configured.
def run_configure(example):
    parser = argparse.ArgumentParser("test")

    # Currently required to run from the example folder
    test_dir = os.getcwd()
    example_path = CASES_DIR / example
    os.chdir(example_path)

    # Rely heavily on defaults (modify output to avoid local changes from test)
    output_dir = example_path / "tmp"
    output_file = output_dir / "test.json"
    if not output_dir.exists():
        output_dir.mkdir()
    sys.argv = ["test", "--output", os.fspath(output_file)]
    myna.core.workflow.config.parse(parser)

    # Check if output file was generated
    assert output_file.exists()

    # Cleanup
    shutil.rmtree(output_dir)
    os.chdir(test_dir)


def test_configure():
    examples = [
        "cluster_solidification",
        "melt_pool_geometry_part",
        "melt_pool_geometry_part_pelican",
        "microstructure_region",
        "microstructure_region_slice",
        "openfoam_meshing",
        "rve_part_center",
        "solidification_build_region",
        "solidification_part",
        "solidification_part_hdf5",
        "solidification_part_json",
        "solidification_part_pelican",
        "solidification_region_reduced",
        "solidification_region_reduced_stl",
        "temperature_part",
        "temperature_part_pvd",
        "vtk_to_exodus_region",
    ]

    for example in examples:
        run_configure(example)
