#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Base classes for metadata requirements that are entire files"""

import shutil
import os


class BuildFile:
    """File that requires a build path specification"""

    def __init__(self, datatype):
        self.datatype = datatype
        self.file_database = ""
        self.file_local = ""
        self.resource_dir = ""
        self.myna_format = (
            False  # For tracking if the file has been converted to Myna format
        )
        self.set_local_resource_dir()

    def copy_file(self, destination=None, overwrite=True):
        """Copy self.file to destination"""

        if destination is None:
            destination = self.file_local
        if not os.path.exists(destination) or overwrite:
            os.makedirs(os.path.abspath(os.path.dirname(destination)), exist_ok=True)
            shutil.copy(self.file_database, destination)

        try:
            self.local_to_myna_format()
        except NotImplementedError:
            pass

    def set_local_resource_dir(self):
        """Get the local resource directory and make if it doesn't exist"""

        input_dir = os.path.abspath(os.path.dirname(os.environ["MYNA_INPUT"]))
        if input_dir is None:
            input_dir = "."
        resource_dir = os.path.abspath(os.path.join(input_dir, "myna_resources"))
        os.makedirs(resource_dir, exist_ok=True)
        self.resource_dir = resource_dir

    def local_to_myna_format(self):
        """Convert the local file to the myna format"""

        raise NotImplementedError


class BuildLayerPartsetFile(BuildFile):
    """File that requires both a build and layer specification"""

    def __init__(self, datatype, partset, layer):
        BuildFile.__init__(self, datatype)
        self.partset = partset
        self.layer = layer


class PartFile(BuildFile):
    """File that requires both a build and part specification"""

    def __init__(self, datatype, part):
        BuildFile.__init__(self, datatype)
        self.part = part
        self.resource_dir = os.path.abspath(os.path.join(self.resource_dir, f"{part}"))


class LayerFile(PartFile):
    """File that requires a build, part, and layer specification"""

    def __init__(self, datatype, part, layer):
        PartFile.__init__(self, datatype, part)
        self.layer = layer
        self.resource_dir = os.path.abspath(os.path.join(self.resource_dir, f"{layer}"))
