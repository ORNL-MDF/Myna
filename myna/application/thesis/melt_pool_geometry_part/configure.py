#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import mistlib as mist
import os
from myna.core.workflow.load_input import load_input
import argparse
import sys
import shutil
import numpy as np
from myna.application.thesis import get_scan_stats, adjust_parameter, Thesis


def configure_case(case_dir, res, nout, myna_input="myna_data.yaml"):
    # Load input file
    input_path = os.path.join(case_dir, myna_input)
    settings = load_input(input_path)

    # Get part and layer info
    part = list(settings["build"]["parts"].keys())[0]
    layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

    # Copy template case
    template_path = os.path.join(
        os.environ["MYNA_INTERFACE_PATH"],
        "thesis",
        "melt_pool_geometry_part",
        "template",
    )
    files = os.listdir(template_path)
    for f in files:
        source = os.path.join(template_path, f)
        dest = os.path.join(case_dir, f)
        shutil.copy(source, dest, follow_symlinks=True)

    # Set up scan path
    myna_scanfile = settings["build"]["parts"][part]["layer_data"][layer]["scanpath"][
        "file_local"
    ]
    case_scanfile = os.path.join(case_dir, "Path.txt")
    shutil.copy(myna_scanfile, case_scanfile)

    # Set up material properties
    material = settings["build"]["build_data"]["material"]["value"]
    material_dir = os.path.join(
        os.environ["MYNA_INSTALL_PATH"], "resources", "mist_material_data"
    )
    try:
        mistPath = os.path.join(material_dir, f"{material}.json")
        mistMat = mist.core.MaterialInformation(mistPath)
        mistMat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))
    except:
        raise Exception(f'Material "{material}" not found in mist material database.')

    # Set preheat temperature
    preheat = settings["build"]["build_data"]["preheat"]["value"]
    adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

    # Set beam data
    beam_file = os.path.join(case_dir, "Beam.txt")
    power = settings["build"]["parts"][part]["laser_power"]["value"]
    spot_size = settings["build"]["parts"][part]["spot_size"]["value"]
    spot_unit = settings["build"]["parts"][part]["spot_size"]["unit"]
    spot_scale = 1
    if spot_unit == "mm":
        spot_scale = 1e-3
    elif spot_unit == "um":
        spot_scale = 1e-6

    # For setting spot size, assume provided spot size is $D4 \sigma$
    # 3DThesis spot size is $\sqrt(6) \sigma$
    adjust_parameter(beam_file, "Width_X", 0.25 * np.sqrt(6) * spot_size * spot_scale)
    adjust_parameter(beam_file, "Width_Y", 0.25 * np.sqrt(6) * spot_size * spot_scale)
    adjust_parameter(beam_file, "Power", power)

    # Update domain resolution
    domain_file = os.path.join(case_dir, "Domain.txt")
    adjust_parameter(domain_file, "Res", res)

    # Update output times
    mode_file = os.path.join(case_dir, "Mode.txt")
    elapsed_time, _ = get_scan_stats(case_scanfile)
    times = np.linspace(0, elapsed_time, nout)
    adjust_parameter(mode_file, "Times", ",".join([str(x) for x in times]))

    return


def main():
    sim = Thesis("melt_pool_geometry_part")

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Configure each case
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        configure_case(case_dir, sim.args.res, sim.args.nout)


if __name__ == "__main__":
    main()
