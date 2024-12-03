#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import shutil
import numpy as np
import mistlib as mist
from myna.core.workflow import load_input
from myna.application.thesis.parse import adjust_parameter
from myna.application.thesis import Thesis


def configure_case(app, case_dir):
    """Configure a 3DThesis case directory from Myna data

    Args:
        app: instance of Thesis (MynaApp)
        case_dir: (str) the path to the case directory to configure
    """
    # Load myna_data.yaml for the case
    settings = load_input(os.path.join(case_dir, "myna_data.yaml"))

    # Get part and layer info
    part = list(settings["build"]["parts"].keys())[0]
    layer = list(settings["build"]["parts"][part]["layer_data"].keys())[0]

    # Copy template to case directory
    if app.args.template is None:
        template_dir = os.path.join(
            os.environ["MYNA_APP_PATH"], "thesis", "solidification_part", "template"
        )
        app.args.template = template_dir
    else:
        template_dir = os.path.abspath(app.args.template)
    shutil.copytree(template_dir, case_dir, dirs_exist_ok=True)

    # Set up scan path
    myna_scanfile = settings["build"]["parts"][part]["layer_data"][layer]["scanpath"][
        "file_local"
    ]
    case_scanfile = os.path.join(case_dir, "Path.txt")
    shutil.copy(myna_scanfile, case_scanfile)

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
    try:
        mist_path = os.path.join(material_dir, f"{material}.json")
        mist_mat = mist.core.MaterialInformation(mist_path)
        mist_mat.write_3dthesis_input(os.path.join(case_dir, "Material.txt"))
        laser_absorption = mist_mat.get_property("laser_absorption", None, None)
        adjust_parameter(beam_file, "Efficiency", laser_absorption)
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f'Material "{material}" not found in mist material database.'
        ) from exc

    # Set preheat temperature
    preheat = settings["build"]["build_data"]["preheat"]["value"]
    adjust_parameter(os.path.join(case_dir, "Material.txt"), "T_0", preheat)

    # Update domain resolution
    domain_file = os.path.join(case_dir, "Domain.txt")
    adjust_parameter(domain_file, "Res", app.args.res)

    return


def main():
    """Configure all 3DThesis cases for a Myna `solidification_part` step"""

    # Create the Thesis app instance
    app = Thesis("solidification_part")

    # Get expected Myna output files and run each case
    myna_files = app.settings["data"]["output_paths"][app.step_name]
    for case_dir in [os.path.dirname(x) for x in myna_files]:
        configure_case(app, case_dir)


if __name__ == "__main__":
    main()
