import argparse

import myna.components
from .load_input import load_input

def main(argv=None):
    '''Main function for running myna from the command line
    
    Parameters
    ----------
    argv : list of str, optional
        List of command line arguments, by default None'''

    # Set up argparse
    parser = argparse.ArgumentParser(description='Launch myna for '+ 
                                     'specified input file')
    parser.add_argument('--input', type=str,
                        help='path to the desired input file to run' + 
                        ', for example: ' + 
                        '--input demo.yaml')

    # Parse cmd arguements
    args = parser.parse_args(argv)
    input_file = args.input

    # Load the initial input file to get the steps
    initial_settings = load_input(input_file)
    
    # Run through each step
    for step in initial_settings["steps"]:

        # Load the input file at each step in case one the previous step has updated the inputs
        settings = load_input(input_file)

        # Get the step name and class
        step_name = [x for x in step.keys()][0]
        component_class_name = step[step_name]["class"]
        step_obj = myna.components.return_step_class(component_class_name)
        step_obj.name = step_name

        # Apply the settings and execute the component
        step_obj.apply_settings(step[step_name], settings["data"])
        step_obj.run_component()


