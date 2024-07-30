import sys
import os
import json
import argparse
from myna.core.workflow.load_input import load_input
from myna.core.components import return_step_class
from myna.core.utils import nested_get
from myna.application.exaca import add_rgb_to_vtk


def main(argv=None):

    parser = argparse.ArgumentParser(description="Launch exaca postprocessing")
    parser.add_argument(
        "--input",
        default="inputs.json",
        type=str,
        help="(str) name of the input JSON in the template directory",
    )

    # Parse args
    args = parser.parse_args(argv)
    input = args.input
    settings = load_input(os.environ["MYNA_RUN_INPUT"])

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Check if case already has valid output
    step_obj = return_step_class(os.environ["MYNA_STEP_CLASS"])
    step_dict = settings["steps"][int(os.environ["MYNA_STEP_INDEX"])]
    step_obj.name = list(step_dict.keys())[0]
    step_obj.apply_settings(step_dict[step_obj.name], settings["data"])
    _, _, files_are_valid = step_obj.get_output_files()

    # Open the myna file and export the RGB fields
    for myna_file, valid in zip(myna_files, files_are_valid):
        if not valid:
            continue
        else:
            # Get reference file
            input_file = os.path.join(os.path.dirname(myna_file), input)
            with open(input_file, "r") as f:
                input_dict = json.load(f)
            ref_file = input_dict["GrainOrientationFile"]

            # Export VTK with RGB
            export_file = myna_file.replace(".vtk", "_rgb.vtk")
            add_rgb_to_vtk(myna_file, export_file, ref_file)


if __name__ == "__main__":
    main(sys.argv[1:])
