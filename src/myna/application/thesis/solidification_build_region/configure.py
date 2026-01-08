#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import mistlib as mist
import os
from myna.core.workflow.load_input import load_input
from myna.application.thesis.parse import adjust_parameter
from myna.application.thesis import get_scan_stats
import shutil
import numpy as np
import polars as pl

from myna.application.thesis import Thesis


def configure_case(case_dir, sim, myna_input="myna_data.yaml"):
    # Load input file
    input_path = os.path.join(case_dir, myna_input)
    settings = load_input(input_path)

    # Copy template case
    sim.copy_template_to_case(case_dir)
    beam_file_template = os.path.join(case_dir, "Beam.txt")

    # Get relevant data from all parts in the build_region
    # Configuration ensures that only the relevant part & layer data is present
    build_region = list(settings["build"].get("build_regions").keys())[0]
    build_region_dict = settings["build"]["build_regions"][build_region]
    parts = build_region_dict["partlist"]
    print_order = settings["build"]["build_data"]["print_order"]["value"]
    elapsed_time = 0.0
    beam_index = 1
    for part in print_order:
        if part in parts:
            # Set up scan path
            layer = list(build_region_dict["parts"][part]["layer_data"].keys())[0]
            myna_scanfile = build_region_dict["parts"][part]["layer_data"][layer][
                "scanpath"
            ]["file_local"]
            case_scanfile = os.path.join(case_dir, f"Path_{beam_index}.txt")
            shutil.copy(myna_scanfile, case_scanfile)

            # Add elapsed time to start of scanpath
            scan_time, _ = get_scan_stats(case_scanfile)
            df_scan = pl.read_csv(case_scanfile, separator="\t")
            wait_dict = df_scan.row(0, named=True)
            wait_dict["Mode"] = 1
            wait_dict["tParam"] = elapsed_time
            df_wait = pl.DataFrame(wait_dict)
            df_scan = pl.concat([df_wait, df_scan])
            df_scan.write_csv(case_scanfile, separator="\t")
            elapsed_time += scan_time

            # Set beam data
            beam_file = os.path.join(case_dir, f"Beam_{beam_index}.txt")
            shutil.copy(beam_file_template, beam_file)
            power = build_region_dict["parts"][part]["laser_power"]["value"]
            spot_size = build_region_dict["parts"][part]["spot_size"]["value"]
            spot_unit = build_region_dict["parts"][part]["spot_size"]["unit"]
            spot_scale = 1
            if spot_unit == "mm":
                spot_scale = 1e-3
            elif spot_unit == "um":
                spot_scale = 1e-6

            # For setting spot size, assume provided spot size is $D4 \sigma$
            # 3DThesis spot size is $\sqrt(6) \sigma$
            adjust_parameter(
                beam_file, "Width_X", 0.25 * np.sqrt(6) * spot_size * spot_scale
            )
            adjust_parameter(
                beam_file, "Width_Y", 0.25 * np.sqrt(6) * spot_size * spot_scale
            )
            adjust_parameter(beam_file, "Power", power)

            # Increment beam_index
            beam_index += 1

    # Set up material properties
    material = settings["build"]["build_data"]["material"]["value"]
    material_dir = os.path.join(os.environ["MYNA_INSTALL_PATH"], "mist_material_data")
    mistPath = os.path.join(material_dir, f"{material}.json")
    mistMat = mist.core.MaterialInformation(mistPath)
    mistMat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))

    # Set preheat temperature
    preheat = settings["build"]["build_data"]["preheat"]["value"]
    adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

    # Update domain resolution
    domain_file = os.path.join(case_dir, "Domain.txt")
    adjust_parameter(domain_file, "Res", sim.args.res)

    # Clean up unused template files
    os.remove(beam_file_template)

    return


def main():

    sim = Thesis()
    sim.class_name = "solidification_build_region"

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Run each case
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        configure_case(case_dir, sim)


if __name__ == "__main__":
    main()
