#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define workflow scripts and modules.

This module defines the functionality of workflow tasks, namely
configuration, running/execution, and syncing of the results.
In general, any module that has a command line interface script
should be located here, as a Myna user will generally interact
with Myna at the workflow-level.

Available modules and scripts:
  myna.core.workflow.config:
    The main function is installed as myna_config command line
    function and extracts the necessary metadata from the database
    to be placed in "myna_resources" directory in the working
    directory.
  myna.core.workflow.run:
    The main function is installed as myna_run command line
    function and execute the specified workflow components
    in the input file.
  myna.core.workflow.sync:
    The main function is installed as myna_sync command line
    function and syncs the result files from a Myna workflow
    back to the database.
  myna.core.workflow.launch_from_peregrine:
    The launch_from_peregrine function is installed as the
    command line script myna_peregrine_launcher to enable
    executing predefined myna workflows from Peregrine software.
    The predefined workflows are defined in the "cli/peregrine_launcher"
    directory located in the root-level repository directory.
  myna.core.workflow.load_input:
    Load and return contents of a myna input file

"""

from . import config
from . import run
from . import sync
from .load_input import *
from .status import *
from .launch_from_peregrine import *
