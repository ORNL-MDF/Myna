"""Base class for Myna file"""


class File:
    def __init__(self, file):
        self.file = file
        self.filetype = None

    def file_is_valid(self):
        """Check if file is valid based on class/subclass requirements"""
        raise NotImplementedError

    def columns_are_valid(self, cols, expected_cols, expected_cols_types):
        if not set(expected_cols).issubset(cols):
            print("\nWARNING: The required headers were not found.")
            print("The following headers were found:")
            print(", ".join(cols))
            print("The correct format is a .csv file with headers:")
            print(", ".join(expected_cols))
            print(", ".join([f"{x}" for x in expected_cols_types]), "\n")
            return False
        return True

    def get_values_for_sync(self, prefix):
        """Get values in format expected for sync"""
        raise NotImplementedError
