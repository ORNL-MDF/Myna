#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading behavior for scan path files in databases"""

from .file import *
import os
import polars as pl


class Scanpath(LayerFile):
    """File containing the scan path for a layer of a part in a build.

    Implemented datatypes:
    - PeregrineDB
    """

    def __init__(self, datatype, part, layer):
        LayerFile.__init__(self, datatype, part, layer)
        self.file_database = None
        if datatype is not None:
            self.file_database = datatype.load(
                type(self), part=self.part, layer=self.layer
            )
        self.file_local = os.path.join(self.resource_dir, "scanpath.txt")

    def load_to_dataframe(self):
        """Loads the Myna-formatted scan path to a polars dataframe

        Current scan path format follows the 3DThesis scan path tab-separated format.

        Example scan path:

        > Mode	X(mm)	Y(mm)	Z(mm)	Pmod	tParam\n
        > 1	203.349	28.520	2.550	0	0.000\n
        > 0	203.438	28.478	2.550	1	0.821\n
        > 0	203.361	28.514	2.550	0	0.077\n"""

        if os.path.exists(self.file_local):
            return pl.read_csv(self.file_local, separator="\t")
        return None
