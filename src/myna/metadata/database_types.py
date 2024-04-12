"""Database classes for handling different types of data object loading"""


def return_datatype_class(datatype_str):
    """Return a corresponding database class object given a string name of the database

    Generally this is meant corresponds with user-input names for the
    database specification in the input file.

    Args:
        datatype_str: string of the database name
    """

    if datatype_str.lower() in ["peregrine", "peregrinedb"]:
        return PeregrineDB
    else:
        print(f"Error: {datatype_str} does not correspond to any implemented database")
        raise NotImplementedError


class PeregrineDB:
    def __init__(self):
        self.description = "Peregrine database structure"
