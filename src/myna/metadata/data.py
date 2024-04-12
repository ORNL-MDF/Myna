"""Define the base classes for metadata requirements"""

import os
import numpy as np
from .database_types import *


class BuildMetadata:
    """Metadata that requires a build path"""

    def __init__(self, datatype, build):
        self.file = ""
        self.value = None
        self.unit = ""
        self.build = build
        self.datatype = datatype
        if self.datatype == PeregrineDB:
            self.file = os.path.join(
                self.build, "Peregrine", "simulation", "buildmeta.npz"
            )
        else:
            print(f"{self.datatype} is not implemented for {type(self)}")
            raise NotImplementedError

    def load_file_data(self):
        """Load all data from self.file"""
        data = None
        if self.datatype == PeregrineDB:
            data = np.load(self.file, allow_pickle=True)
            return data
        else:
            print(f"{self.datatype} is not implemented for {type(self)}")
            raise NotImplementedError

    def value_from_file(self):
        """Get the data value from self.file"""
        raise NotImplementedError


class PartMetadata(BuildMetadata):
    """Data that requires both a build and part path"""

    def __init__(self, datatype, build, part):
        BuildMetadata.__init__(self, datatype, build)
        self.part = part
        if self.datatype == PeregrineDB:
            self.file = os.path.join(
                self.build, "Peregrine", "simulation", part, "part.npz"
            )
        else:
            print(f"{self.datatype} is not implemented for {type(self)}")
            raise NotImplementedError
