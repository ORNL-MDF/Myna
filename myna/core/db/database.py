#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the requirements and behavior of the base Myna Database class."""


class Database:
    """The base class for a Myna database"""

    synonyms = {}

    def __init__(self):
        self.description = ""
        self.path = None
        self.path_dir = None

    def load(self, metadata_type):
        """Load and return a metadata value"""
        raise NotImplementedError

    def set_path(self, path):
        """Set the path for the database"""
        raise NotImplementedError

    def get_cui_info(self):
        return NotImplementedError

    def exists(self):
        """Check if database exists at the specified path"""
        raise NotImplementedError

    def sync(self, component_type, step_types, output_class, files):
        """Sync files resulting from a workflow step to the database"""
        raise NotImplementedError
