#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define metadata that can be extracted from databases
into the Myna data format.

There are two modules that define the base classes of
metadata currently implemented:

  myna.metadata.data:
    Defines the BuildMetadata and the PartMetadata classes
    for the extraction of values from a larger file. The value
    of the metadata is expected to be a Python datatype.
  myna.metadata.file:
    Define the BuildFile, PartFile, and LayerFile classes
    for metadata requirements that need the entire file. For
    example, scan path files.
"""

# Import all metadata data classes
from .data import *
from .data_spot_size import *
from .data_material import *
from .data_laser_power import *
from .data_layer_thickness import *
from .data_preheat import *
from .data_print_order import *

# Import all metadata file classes
from .file import *
from .file_scanpath import *
from .file_stl import *
from .file_part_id_map import *

# Import metadata data class name lookup
from .data_class_lookup import *
