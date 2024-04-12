"""Define loading behavior for STL geometry files in databases"""

from .file import *
import os
from .database_types import *


class STL(PartFile):
    """File containing the STL for a part in a build.

    Implemented datatypes:
    - PeregrineDB"""

    def __init__(self, datatype, build, part):
        PartFile.__init__(self, datatype, build, part)
        if self.datatype == PeregrineDB:
            self.file_database = os.path.join(
                self.build, "Peregrine", "simulation", part, f"part.stl"
            )
        else:
            print(f"{self.datatype} is not implemented for {type(self)}")
            raise NotImplementedError
        self.file_local = os.path.join(self.resource_dir, "part.stl")
