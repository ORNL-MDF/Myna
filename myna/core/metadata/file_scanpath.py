"""Define loading behavior for scan path files in databases"""

from .file import *
import os


class Scanpath(LayerFile):
    """File containing the scan path for a layer of a part in a build.

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, build, part, layer):
        LayerFile.__init__(self, datatype, build, part, layer)
        self.file_database = datatype.load(
            self, self.build, part=self.part, layer=self.layer
        )
        self.file_local = os.path.join(self.resource_dir, "scanpath.txt")
