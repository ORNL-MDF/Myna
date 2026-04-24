#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.application.rve.rve_part_center import RVEPartCenter


def main():
    app = RVEPartCenter()
    app.postprocess()


if __name__ == "__main__":
    main()
