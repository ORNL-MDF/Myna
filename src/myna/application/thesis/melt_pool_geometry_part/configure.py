#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import glob
import shutil
import tempfile
from pathlib import Path
import numpy as np
import mistlib as mist
from myna.core.workflow.load_input import load_input
from myna.core.metadata import Scanpath
from myna.application.thesis import (
    get_scan_stats,
    get_initial_wait_time,
    get_final_wait_time,
    adjust_parameter,
    Thesis,
)


def configure_case(case_dir, sim, myna_input="myna_data.yaml"):
    # Load input file
    input_path = os.path.join(case_dir, myna_input)
    settings = load_input(input_path)

    # Get part and layer info
    part = list(settings["build"]["parts"].keys())[0]
    layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

    # Copy template case
    sim.copy(case_dir)

    # Set up scan path
    scan_obj = Scanpath(None, part, layer)
    myna_scanfile = scan_obj.file_local
    case_scanfile = os.path.join(case_dir, "Path.txt")
    shutil.copy(myna_scanfile, case_scanfile)

    # Check if scanfile has multiple z-values
    index_pairs, df = scan_obj.get_constant_z_slice_indices()

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

    # Set up material properties
    material = settings["build"]["build_data"]["material"]["value"]
    material_dir = os.path.join(os.environ["MYNA_INSTALL_PATH"], "mist_material_data")
    mistPath = os.path.join(material_dir, f"{material}.json")
    mistMat = mist.core.MaterialInformation(mistPath)
    mistMat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))
    laser_absorption = mistMat.get_property("laser_absorption", None, None)
    adjust_parameter(beam_file, "Efficiency", laser_absorption)

    # Set preheat temperature
    preheat = settings["build"]["build_data"]["preheat"]["value"]
    adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

    # Update domain resolution
    domain_file = os.path.join(case_dir, "Domain.txt")
    adjust_parameter(domain_file, "Res", sim.args.res)

    # For each index pair, create a separate case
    pattern = str(Path(case_dir) / "*.txt")
    configured_case_files = sorted(glob.glob(pattern))
    elapsed_time = 0.0
    for index, pair in enumerate(index_pairs):
        segment_dir = Path(case_dir) / f"path_segment_{index:03}"
        os.makedirs(segment_dir, exist_ok=True)
        # Copy files from base configured directory
        for case_file in configured_case_files:
            shutil.copy(case_file, segment_dir / Path(case_file).name)
        # Write segment path
        # Start from beginning of path to capture accumulated heat
        segment_scanfile = segment_dir / "Path.txt"
        df_segment = df[0 : pair[1] + 1]
        df_segment.write_csv(segment_scanfile, separator="\t")

        # Write temporary path file for getting elapsed time of the segment to calculate
        # the write times for the melt pool geometry:
        # - Ignore wait times at beginning and end of the scan segment
        # - Distribute `nout` proportionally by segment row count
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            df_segment_only = df[pair[0] : pair[1] + 1]
            df_segment_only.write_csv(fp.name, separator="\t")
            fp.close()
            segment_time, _ = get_scan_stats(fp.name)
            segment_time_wait_ini = get_initial_wait_time(fp.name)
            segment_time_wait_fin = get_final_wait_time(fp.name)
            fraction_segments = int(sim.args.nout * (len(df_segment_only) / len(df)))
            segment_times = np.linspace(
                elapsed_time + segment_time_wait_ini,
                elapsed_time + segment_time - segment_time_wait_fin,
                fraction_segments,
            )
        elapsed_time += segment_time

        # Update output times
        mode_file = segment_dir / "Mode.txt"
        adjust_parameter(
            str(mode_file), "Times", ",".join([str(x) for x in segment_times])
        )

    return


def main():
    sim = Thesis("melt_pool_geometry_part")

    # Get expected Myna output files
    myna_files = sim.settings["data"]["output_paths"][sim.step_name]

    # Configure each case
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        configure_case(case_dir, sim)


if __name__ == "__main__":
    main()
