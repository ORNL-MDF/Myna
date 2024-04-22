"""Define the base classes for metadata requirements"""


class BuildMetadata:
    """Metadata that requires a build path"""

    def __init__(self, datatype, build):
        self.value = None
        self.unit = ""
        self.build = build
        self.datatype = datatype

    def value_from_database(self):
        value = self.datatype.load(self, self.build)
        return value


class PartMetadata(BuildMetadata):
    """Data that requires both a build and part path"""

    def __init__(self, datatype, build, part):
        BuildMetadata.__init__(self, datatype, build)
        self.part = part

    def value_from_database(self):
        value = self.datatype.load(self, self.build, part=self.part)
        return value
