#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Postprocess script wrapper for rve/rve_selection."""

from myna.application.rve.rve_selection.app import RVESelection


def postprocess():
    """Postprocess all case directories."""
    app = RVESelection()
    app.postprocess()


if __name__ == "__main__":
    postprocess()
