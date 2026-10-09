#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines ``myna validate`` functionality."""

import os

from myna.core import components
from myna.core.context import workflow_context, workflow_env
from myna.core.workflow.load_input import load_input
from myna.core.utils import str_to_list


def parse(parser):
    """Add and parse arguments for executable validation."""
    parser.add_argument(
        "--input",
        default="input.yaml",
        type=str,
        help='(str, default="input.yaml") path to the desired input file',
    )
    parser.add_argument(
        "--step",
        type=str,
        help="step or comma-separated steps to validate; validates all by default",
    )
    args = parser.parse_args()
    validate(args.input, args.step)


def validate(input_file, step=None):
    """Validate executable requirements without modifying workflow files."""
    input_file = os.path.abspath(input_file)
    settings = load_input(input_file)
    selected_steps = str_to_list(step)

    for index, step_settings in enumerate(settings.get("steps", [])):
        step_name = next(iter(step_settings))
        if selected_steps is not None and step_name not in selected_steps:
            continue
        values = step_settings[step_name]
        step_obj = components.return_step_class(values["class"])
        step_obj.name = step_name
        step_obj.component_class = values["class"]
        step_obj.component_application = values["application"]
        step_obj.input_file = input_file
        step_obj.step_index = index
        step_obj.apply_settings(values, settings.get("data"), settings.get("myna"))
        with workflow_context(
            input_file=input_file,
            step_name=step_name,
            step_class=values["class"],
            step_index=index,
        ) as context:
            with workflow_env(context, operation="validate"):
                step_obj.validate_executables()
        print(f"Validated executables for step {step_name}.")
