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
import argparse
import myna
import sys

from .example_paths import DATABASES_DIR, REPO_ROOT


# This test checks that the Peregrine CLI is behaving as expected for a test call
def test_peregrine_cli():
    build_dir = DATABASES_DIR
    output_dir = build_dir / "Myna"
    tmp_dir = os.path.abspath("myna_tmp")

    # Set up command line argument
    parser = argparse.ArgumentParser("test")
    sys.argv = [
        "test",
        "--build",
        os.fspath(build_dir),
        "--parts",
        "[P5]",
        "--layers",
        "[50]",
        "--workspace",
        os.fspath(
            REPO_ROOT
            / "src"
            / "myna"
            / "cli"
            / "peregrine_launcher"
            / "peregrine_default_workspace.yaml"
        ),
        "--mode",
        "meltpool_geometry",
        "--tmp-dir",
        f"{tmp_dir}",
    ]
    myna.core.workflow.launch_from_peregrine(parser)

    assert os.path.exists(output_dir)
    shutil.rmtree(output_dir)
    shutil.rmtree(tmp_dir)
