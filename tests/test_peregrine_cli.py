#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import pytest
import os
import shutil
import argparse
import myna
import sys


# This test checks that the Peregrine CLI is behaving as expected for a test call
def test_peregrine_cli():
    test_path = os.path.dirname(os.path.abspath(__file__))
    myna_path = os.path.abspath(os.path.join(test_path, ".."))
    build_dir = os.path.join(myna_path, "resources")
    output_dir = os.path.join(build_dir, "Myna")

    # Set up command line argument
    parser = argparse.ArgumentParser("test")
    sys.argv = [
        "test",
        "--build",
        f"{build_dir}",
        "--parts",
        "[P5]",
        "--layers",
        "[50]",
        "--workspace",
        f"{myna_path}/cli/peregrine_launcher/peregrine_default_workspace.yaml",
        "--mode",
        "meltpool_geometry",
        "--tmp-dir",
        "~/myna_tmp",
    ]
    myna.core.workflow.launch_from_peregrine(parser)

    assert os.path.exists(output_dir)
    shutil.rmtree(output_dir)
