#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the requirements and behavior of the base Myna Database class."""

import os
from datetime import datetime
import yaml
from myna.core.workflow import load_input
from myna.core.utils import strf_datetime


class Database:
    """The base class for a Myna database"""

    synonyms = {}

    def __init__(self):
        self.description = ""
        self.path = None
        self.path_dir = None
        self.build_segmentation_type = None

    def load(self, metadata_type):
        """Load and return a metadata value"""
        raise NotImplementedError

    def set_path(self, path):
        """Set the path for the database"""
        raise NotImplementedError

    def get_cui_info(self):
        raise NotImplementedError

    def exists(self):
        """Check if database exists at the specified path"""
        raise NotImplementedError

    def sync(self, component_type, step_types, output_class, files):
        """Sync files resulting from a workflow step to the database"""
        raise NotImplementedError

    def write_segment_sync_metadata(
        self, sync_metadata_file, simulation_file_path, segment_key
    ):
        """Write metadata for a file being synced to the database

        Args:
            sync_metadata_file (str): Path to the YAML file where metadata is stored
            simulation_file_path (str): Path to the simulation file being synced
            segment_key (str): Key identifying the segment in the database"""
        step_name = os.path.basename(os.path.dirname(simulation_file_path))
        step_list = load_input(os.environ["MYNA_INPUT"])["steps"]
        step_dict = step_list[
            [list(step.keys())[0] for step in step_list].index(step_name)
        ]
        if os.path.exists(sync_metadata_file):
            with open(sync_metadata_file, "r", encoding="utf-8") as mf:
                sync_dict = yaml.safe_load(mf)
        else:
            sync_dict = {}
        segment_type_key = f"{self.build_segmentation_type}_segment"
        if segment_type_key not in sync_dict:
            sync_dict[segment_type_key] = {}
        if segment_key not in sync_dict[segment_type_key]:
            sync_dict[segment_type_key][segment_key] = {}
        sync_dict[segment_type_key][segment_key] = step_dict[step_name]
        sync_dict[segment_type_key][segment_key]["simulation_data_last_modified"] = (
            strf_datetime(
                datetime.fromtimestamp(os.path.getmtime(simulation_file_path))
            )
        )

        sync_dict[segment_type_key][segment_key]["synced_on"] = strf_datetime(
            datetime.now()
        )
        sync_dict[segment_type_key][segment_key]["synced_by"] = os.getlogin()
        with open(sync_metadata_file, "w", encoding="utf-8") as mf:
            yaml.safe_dump(sync_dict, mf)
