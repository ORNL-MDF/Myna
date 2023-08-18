import argparse
import os
import yaml
from .load_input import load_input
import myna.components
import myna.peregrine

def main(argv=None):
    '''Main function for configuring myna data from the command line
    
    Parameters
    ----------
    argv : list of str, optional
        List of command line arguments, by default None'''

    # Set up argparse
    parser = argparse.ArgumentParser(description='Configure myna data for '+ 
                                     'specified input file')
    parser.add_argument('--input', type=str,
                        help='path to the desired input file to run' + 
                        ', for example: ' + 
                        '--input demo.yaml')
    parser.add_argument('--avail', default=False, action='store_true',
                        help='switch to show all available data files, but will' +
                        'not update input file data values')

    # Parse cmd arguements
    args = parser.parse_args(argv)
    input_file = args.input
    show_avail = args.avail

    # Load input file
    settings = load_input(input_file)

    # Check build diretory exists with Peregrine data folder
    build_path = settings["data"]["build"]["path"]
    peregrine_path = os.path.join(build_path, "Peregrine")
    has_peregrine = os.path.isdir(peregrine_path)
    if not has_peregrine:
        print("ERROR: Could not find valid Peregrine folder in" +
                f" {build_path}")
        exit(1)
    
    # Get part names
    parts = settings["data"]["parts"]
    if len(parts) < 1:
        print(f"ERROR: No data/parts specified in {input_file}")
        exit(1)

    # Check if {"data": {"output_paths":}} key  and create if not
    value = settings["data"].get("output_paths")
    if value is None:
        settings["data"]["output_paths"] = {}

    # If specified, get available data. Otherwise extract necessary data
    if show_avail:
        print("Available Peregrine data:\n-------------------------")
        last_path = ""
        for path, dirs, files in os.walk(peregrine_path):
            for f in files:
                if len(dirs) == 0:
                    if last_path is not path: print(path)
                    print("    "*(len(dirs) + 1), f)
                    last_path = path

    
    else:
        # Determine which data needs to be added based on component class requirements
        for step in settings["steps"]:
            # Get the step component class name
            step_name = [x for x in step.keys()][0]
            component_class_name = step[step_name]["class"]
            print(f"- Configuring step {step_name} ({component_class_name})")
            step_obj = myna.components.return_step_class(component_class_name)
            step_obj.name = step_name

            # Get the data requirements associated with that class
            for data_req in step_obj.data_requirements:

                # For each data requirements, lookup the corresponding data object
                data_class_name = myna.peregrine.return_data_class_name(data_req)
                constructor = vars(myna.peregrine)[data_class_name]

                # Depending on if it is a part of a build value, construct the relevant object
                if constructor.__base__ == myna.peregrine.PeregrineBuildData:
                    data_obj = constructor(build_path)
                    settings["data"]["build"][data_req] = {}
                    settings["data"]["build"][data_req]["value"] = data_obj.value
                    settings["data"]["build"][data_req]["unit"] = data_obj.unit
                if constructor.__base__ == myna.peregrine.PeregrinePartData:
                    for part in parts.keys():
                        data_obj = constructor(build_path, part)
                        settings["data"]["parts"][part][data_req] = {}
                        settings["data"]["parts"][part][data_req]["value"] = data_obj.value
                        settings["data"]["parts"][part][data_req]["unit"] = data_obj.unit
            
            # Set the outputs associated with the step
            if step_obj.output_requirement is not None:
                print(f"  > Expecting output for step \"{step_name}\":")
                step_obj.apply_settings(step[step_name], settings["data"])
                output_files = step_obj.get_output_files()
                for f in output_files:
                    print(f"    - {f}")
                settings["data"]["output_paths"][step_name] = output_files

    with open(input_file, "w") as f:
        yaml.dump(settings, f, sort_keys=False, default_flow_style=None)

    
                        
                        


