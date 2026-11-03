#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""External simulation application module for the Myna workflow framework."""

from importlib import import_module

__all__ = [
    "adamantine",
    "additivefoam",
    "bnpy",
    "cubit",
    "deer",
    "exaca",
    "openfoam",
    "rve",
    "thesis",
]


def __getattr__(name):
    """Lazily import application backends."""

    if name in __all__:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
