#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the base classes for metadata requirements"""


class BuildMetadata:
    """Metadata that is associated with a build"""

    def __init__(self, datatype):
        self.value = None
        self.unit = ""
        self.datatype = datatype

    def value_from_database(self):
        value = self.datatype.load(type(self), self.datatype.path)
        return value


class PartMetadata(BuildMetadata):
    """Data that requires both a build and part path"""

    def __init__(self, datatype, part):
        BuildMetadata.__init__(self, datatype)
        self.part = part

    def value_from_database(self):
        value = self.datatype.load(type(self), part=self.part)
        return value
