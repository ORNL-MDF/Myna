#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#

import subprocess
import os
import shutil
import numpy as np


def set_beam_size(case_dir, spot_x, spot_y):
    """Sets the beam size for an AdditiveFOAM case

    Args:
        case_dir: path to the case directory to modify
        spot_x: x-dimension of the heat source (radius of beam with diameter 4Dsigma)
                in meters
        spot_y: y-dimension of the heat source (radius of beam with diameter 4Dsigma)
                in meters
    """

    # 1. Get heatSourceModel
    heat_source_model = (
        subprocess.check_output(
            f"foamDictionary -entry beam/heatSourceModel -value "
            + f"{case_dir}/constant/heatSourceDict",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )

    # 2. Get heatSourceModelCoeffs/dimensions
    heat_source_dimensions = (
        subprocess.check_output(
            f"foamDictionary -entry beam/{heat_source_model}Coeffs/dimensions -value "
            + f"{case_dir}/constant/heatSourceDict",
            shell=True,
        )
        .decode("utf-8")
        .strip()
    )
    heat_source_dimensions = (
        heat_source_dimensions.replace("(", "").replace(")", "").strip()
    )
    heat_source_dimensions = [float(x) for x in heat_source_dimensions.split(" ")]

    # 3. Modify X- and Y-dimensions
    heat_source_dimensions[:2] = [spot_x, spot_y]
    heat_source_dimensions = [round(dim, 7) for dim in heat_source_dimensions]

    # 4. Write to file
    heat_source_dim_string = (
        str(heat_source_dimensions)
        .replace("[", "( ")
        .replace("]", " )")
        .replace(",", "")
    )
    os.system(
        f"foamDictionary -entry beam/{heat_source_model}Coeffs/dimensions -set"
        + f" {heat_source_dim_string}"
        + f" {case_dir}/constant/heatSourceDict"
    )


def set_start_and_end_times(
    case_dir, start_time, end_time, time_precision=5, num_write_times=None
):
    """Updates the case to have the given start and end times

    Args:
        case_dir: path to case directory to update
        start_time: time to start the simulation, in seconds
        end_time: time to end the simulation, in seconds
        time_precision: decimal precision for time entries
        num_write_times: number of time steps to write out, if not specified (None)
                         only the last time step will be output"""

    # Set start and end times and rename initial condition directory
    start_time = np.round(start_time, time_precision)
    end_time = np.round(end_time, time_precision)
    os.system(
        f"foamDictionary -entry startTime -set {start_time} "
        + f"{case_dir}/system/controlDict"
    )
    os.system(
        f"foamDictionary -entry endTime -set {end_time} "
        + f"{case_dir}/system/controlDict"
    )
    shutil.move(os.path.join(case_dir, "0"), os.path.join(case_dir, f"{start_time}"))

    # Calculate and set write interval
    if (num_write_times is None) or (num_write_times == 0):
        write_interval = np.round((end_time - start_time), time_precision)
    else:
        write_interval = np.round(
            1 / num_write_times * (end_time - start_time), time_precision
        )
    os.system(
        f"foamDictionary -entry writeInterval -set"
        + f" {write_interval}"
        + f" {case_dir}/system/controlDict"
    )
    shutil.move(os.path.join(case_dir, "0"), os.path.join(case_dir, f"{start_time}"))
