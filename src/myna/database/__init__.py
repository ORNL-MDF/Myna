#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database implementations.

Database adapters are imported when their public symbol is accessed so that
users can use an unrelated adapter without loading every adapter's dependencies.
"""

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .database_types import return_datatype_class
    from .myna_json import MynaJSON
    from .nist_ambench_2022 import AMBench2022
    from .pelican import Pelican
    from .peregrine_hdf5 import PeregrineHDF5
    from .peregrine import PeregrineDB

__all__ = [
    "return_datatype_class",
    "MynaJSON",
    "AMBench2022",
    "Pelican",
    "PeregrineHDF5",
    "PeregrineDB",
]

_EXPORT_MODULES = {
    "return_datatype_class": ".database_types",
    "MynaJSON": ".myna_json",
    "AMBench2022": ".nist_ambench_2022",
    "Pelican": ".pelican",
    "PeregrineHDF5": ".peregrine_hdf5",
    "PeregrineDB": ".peregrine",
}


def __getattr__(name):
    """Lazily import a public database adapter or lookup function."""

    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
