"""Define loading behavior for STL geometry files in databases"""

from .file import *
import os


class STL(PartFile):
    """File containing the STL for a part in a build.

    Implemented datatypes:
    - PeregrineDB"""

    def __init__(self, datatype, build, part):
        PartFile.__init__(self, datatype, build, part)
        self.file_database = datatype.load(self, self.build, part=self.part)
        self.file_local = os.path.join(self.resource_dir, "part.stl")
