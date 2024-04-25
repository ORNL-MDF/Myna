"""Define loading behavior for STL geometry files in databases"""

from .file import *
import os


class STL(PartFile):
    """File containing the STL for a part in a build.

    Implemented datatypes:
    - PeregrineDB"""

    def __init__(self, datatype, part):
        PartFile.__init__(self, datatype, part)
        self.file_database = datatype.load(type(self), part=self.part)
        self.file_local = os.path.join(self.resource_dir, "part.stl")
