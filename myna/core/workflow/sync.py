"""Defines `myna sync` functionality"""

import os
import argparse
import myna.core.utils
import myna.core.components
import myna.database
from myna.core.workflow.load_input import load_input


# Parser comes from the top-level command parsing
def main(parser):
    """Main function for syncing myna data back to a database"""

    parser.add_argument(
        "--input",
        default="input.yaml",
        type=str,
        help='(str, default="input.yaml") path to the desired input file to run',
    )
    parser.add_argument(
        "--step",
        type=str,
        help="(str) step or steps to run from the given input file."
        + ' For one step use "--step step_name" and'
        + ' for multiple steps use "--step [step_name_0,step_name_1]"',
    )

    # Parse cmd arguments
    args = parser.parse_args(argv)
    input_file = args.input
    steps_to_sync = myna.core.utils.str_to_list(args.step)

    # Set environmental variable for input file location
    os.environ["MYNA_SYNC_INPUT"] = os.path.abspath(input_file)

    # Load the initial input file to get the steps
    initial_settings = load_input(input_file)

    # Run through each step
    for index, step in enumerate(initial_settings["steps"]):
        # Load the input file at each step in case one the previous step has updated the inputs
        settings = load_input(input_file)

        # Get the step name and class
        step_name = [x for x in step.keys()][0]
        component_class_name = step[step_name]["class"]
        component_interface_name = step[step_name]["interface"]
        step_obj = myna.core.components.return_step_class(component_class_name)
        step_obj.name = step_name
        step_obj.component_class = component_class_name
        step_obj.component_interface = component_interface_name

        # Set environmental variable for the step name
        if index != 0:
            os.environ["MYNA_LAST_STEP_NAME"] = os.environ["MYNA_STEP_NAME"]
            os.environ["MYNA_LAST_STEP_CLASS"] = os.environ["MYNA_STEP_CLASS"]
        else:
            os.environ["MYNA_LAST_STEP_NAME"] = ""
            os.environ["MYNA_LAST_STEP_CLASS"] = ""
        os.environ["MYNA_STEP_NAME"] = step_name
        os.environ["MYNA_STEP_CLASS"] = component_class_name
        os.environ["MYNA_STEP_INDEX"] = str(index)

        # Apply the settings and execute the component, as needed
        sync_step = True
        if steps_to_sync is not None:
            if step_name not in steps_to_sync:
                print(
                    f"Skipping step {step_name}: Step is not in"
                    + " the specified steps to run."
                )
                sync_step = False
        if sync_step:
            step_obj.apply_settings(step[step_name], settings["data"])
            step_obj.sync_output_files()
