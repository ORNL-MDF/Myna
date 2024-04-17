"""Define loading behavior for scan path files in databases"""

from .file import *
import os
from .database_types import *


class Scanpath(LayerFile):
    """File containing the scan path for a layer of a part in a build.

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build, part, layer):
        LayerFile.__init__(self, datatype, build, part, layer)
        if self.datatype == PeregrineDB:
            self.file_database = os.path.join(
                self.build, "Peregrine", "simulation", part, f"{int(layer):07d}.txt"
            )
        else:
            print(f"{self.datatype} is not implemented for {type(self)}")
            raise NotImplementedError
        self.file_local = os.path.join(self.resource_dir, "scanpath.txt")
