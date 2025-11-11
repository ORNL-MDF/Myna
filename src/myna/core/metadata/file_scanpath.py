#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define loading behavior for scan path files in databases"""

import os
import polars as pl
from .file import LayerFile


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

    def get_constant_z_slice_indices(self) -> tuple[list[tuple], pl.DataFrame]:
        """If scanfile has multiple z-values, then find the slices of the scan
        segments that have constant z-values

        Returns a list of tuples of the starting and ending row indices for the
        segments and the associated polars DataFrame. For example, if there are two
        equal "layers" of constant z-heights in the same scan path file with 200 layers,
        this would output `([(0,99), (100,199)], df)`"""
        index_0 = 0
        index_1 = -1
        z_0 = None
        index_pairs = []
        df = self.load_to_dataframe()
        for index, (row) in enumerate(df.iter_rows(named=True)):

            # If at the start, set current z-value and start index
            if z_0 is None:
                index_0 = index
                z_0 = row["Z(mm)"]

            # If the same z-value as the last row, update end index
            elif z_0 == row["Z(mm)"]:
                index_1 = index

            # If not the same z-value as the last row, record the start and end indices
            # and update the z-value
            else:
                z_0 = row["Z(mm)"]
                index_pairs.append((index_0, index_1))
                index_0 = index

        # Handle if there is only one segment
        if len(index_pairs) == 0:
            index_pairs.append((0, df.shape[0]))

        # Handle last segment if there are multiple segments
        elif (index_0, index_1) != index_pairs[-1]:
            index_pairs.append((index_0, index_1))

        return (index_pairs, df)
