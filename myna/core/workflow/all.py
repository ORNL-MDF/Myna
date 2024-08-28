#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines all `myna` command line functionality"""

import argparse

import myna


def main():
    """Main function for any myna workflow from the command line"""

    # Set up argparse
    parser = argparse.ArgumentParser(description="Setup myna")
    parser.add_argument(
        "type",
        action="store",
        nargs="+",
        help='Run one or more stages of the myna workflow: "config", "run", "sync". Or output the current "status" or "launch_peregrine"',
    )

    # Only parse known argument (type) since others will only be used per-step.
    args, _ = parser.parse_known_args()
    if "status" in args.type:
        myna.core.workflow.status.write_codebase_status_to_file(parser)
    elif "launch_peregrine" in args.type:
        myna.core.workflow.launch_from_peregrine(parser)
    else:
        if "config" in args.type:
            myna.core.workflow.config.main(parser)
        if "run" in args.type:
            myna.core.workflow.run.main(parser)
        if "sync" in args.type:
            myna.core.workflow.sync.main(parser)
