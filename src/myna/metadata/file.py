"""Base classes for file requirements"""
import shutil
import os


class BuildFile:
    """File that requries a build path"""

    def __init__(self, datatype, build):
        self.datatype = datatype
        self.file_database = ""
        self.file_local = ""
        self.resource_dir = ""
        self.build = build
        self.myna_format = (
            False  # For tracking if the file has been converted to Myna format
        )
        self.set_local_resource_dir()

    def copy_file(self, destination=None):
        """Copy self.file to destination"""
        if destination is None:
            destination = self.file_local
        os.makedirs(os.path.abspath(os.path.dirname(destination)), exist_ok=True)
        shutil.copy(self.file_database, destination)

    def set_local_resource_dir(self):
        """Get the local resource directory and make if it doesn't exist"""
        resource_dir = os.path.abspath(os.path.join(".", "myna_resources"))
        os.makedirs(resource_dir, exist_ok=True)
        self.resource_dir = resource_dir

    def local_to_myna_format(self):
        """Convert the local file to the myna format"""
        raise NotImplementedError


class PartFile(BuildFile):
    """Data that requries both a build and part path"""

    def __init__(self, datatype, build, part):
        BuildFile.__init__(self, datatype, build)
        self.part = part
        self.resource_dir = os.path.abspath(os.path.join(self.resource_dir, f"{part}"))


class LayerFile(BuildFile):
    """Data that requries both a build and part path"""

    def __init__(self, datatype, build, part, layer):
        PartFile.__init__(self, datatype, build, part)
        self.layer = layer
        self.resource_dir = os.path.abspath(os.path.join(self.resource_dir, f"{layer}"))
