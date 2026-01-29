#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Myna core functionality.

Provides classes required to link databases and simulation workflow steps
for additive manufacturing process-structure-property simulations (and
possibly other applications).

Documentation is provided in docstrings, the root-level readme, and in
readme files within the "myna/application" and "examples" subdirectories.

Available subpackages:
  components:
    Defines general functionality for a workflow component, i.e., a workflow step,
    and create subclasses that define specific requirements for metadata,
    input file format, and output file format for a given workflow step.
  files:
    Defines file formats that are associated with various components to
    ensure that the output files from applications are compatible with
    proceeding components, regardless of the application backend.
  metadata:
    Defines types of metadata that can be accessed by components and
    provides the required functionality to extract each piece of metadata
    from implemented databases.
  utils:
    Utility functions that are used throughout this package and in the
    applications.
  workflow:
    Modules that handle configuring, running, and syncing Myna workflow
    steps based on the specified database.
"""

import os

# Set environment variables on package import
os.environ["MYNA_INSTALL_PATH"] = os.path.sep.join(
    os.path.abspath(__file__).split(os.path.sep)[:-2]
)

os.environ["MYNA_APP_PATH"] = os.path.join(
    os.path.sep.join(os.path.abspath(__file__).split(os.path.sep)[:-2]),
    "application",
)

# Submodules
from . import metadata
from . import components
from . import files
from . import workflow
from . import utils
from . import db

__all__ = [
    "metadata",
    "components",
    "files",
    "workflow",
    "utils",
    "db",
]
