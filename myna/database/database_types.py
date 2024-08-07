#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database classes for handling different types of data object loading"""

from myna.database.peregrine import PeregrineDB
from myna.database.peregrine_hdf5 import PeregrineHDF5


def return_datatype_class(datatype_str):
    """Return a corresponding database class object given a string name of the database

    Generally this is meant corresponds with user-input names for the
    database specification in the input file.

    Args:
        datatype_str: string of the database name
    """

    if datatype_str.lower() in ["peregrine", "peregrinedb"]:
        return PeregrineDB()
    elif any(
        [
            x in datatype_str.lower()
            for x in ["peregrineh5", "peregrinehdf5", "hdf5", "h5"]
        ]
    ):
        info = datatype_str.lower().split("_")
        if len(info) > 1:
            version = "_".join(info[1:])
            return PeregrineHDF5(version=version)
        else:
            return PeregrineHDF5()
    else:
        print(f"Error: {datatype_str} does not correspond to any implemented database")
        raise NotImplementedError
