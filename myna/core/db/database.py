"""Define the requirements and behavior of the base Myna Database class."""


class Database:
    """The base class for a Myna database"""

    def __init__(self):
        self.description = ""
        self.path = None
        self.path_dir = None

    def load(self, metadata_type):
        """Load and return a metadata value"""
        raise NotImplementedError

    def set_path(self, path):
        """Set the path for the database"""
        raise NotImplementedError

    def exists(self):
        """Check if database exists at the specified path"""
        raise NotImplementedError

    def sync(self, component_type, step_types, output_class, files):
        """Sync files resulting from a workflow step to the database"""
        raise NotImplementedError
