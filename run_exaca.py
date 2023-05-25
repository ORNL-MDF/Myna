import os
from shutil import copytree, ignore_patterns
import numpy as np
import glob
import json



def nested_set(dict, keys, value):
    ''' modifies a nested dictionary value given a list of keys to the nested location'''
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value



def create_cases(settings) :
    ''' create exaca case directories '''
    exaca_cases = []
    for case in settings["autofoam"]["results"]:
        template = settings["exaca"]["template"]
        source = template["path"]
        target = os.path.join(settings["exaca"]["case_dir"], os.path.basename(case))
        exaca_cases.append(target)

        # Create target directory
        ignore_files = [template["material_file"], "GrainOrientation*.csv"]
        copytree(source, 
                 target, 
                 ignore=ignore_patterns(*ignore_files), 
                 dirs_exist_ok=True)
        
        # Get dictionary from target input file
        target_input = os.path.join(target, template["input_file"])
        with open(target_input, 'r') as f:
            input_dict = json.load(f)

        # Update the input dictionary for each specified parameter
        inputs = [x for x in settings["exaca"]["inputs"]]
        for input in inputs :
            
            # Set independent variables
            keys = input["variable"]
            nested_set(input_dict, keys, input["value"])

            # Calculate and set dependent variables
            dependents = input.get("dependents")
            if (dependents) :
                for dependent in dependents:
                    value = dependent["scale"]*input["value"]
                    keys = dependent["variable"]
                    nested_set(input_dict, keys, value)

        # Update the input dictionary file paths
        rel_path = settings["exaca"]["case_dir"].split("results" + os.path.sep)[-1]
        rel_path = os.path.join(f'{settings["exaca"]["case_path_var"]}', rel_path)
        rel_path = os.path.join(rel_path, os.path.basename(case) + os.path.sep)
        nested_set(
            input_dict,
            ["Printing", "PathToOutput"],
            rel_path)

        rel_path = case.split("results" + os.path.sep)[-1]
        rel_path = os.path.join(f'{settings["exaca"]["case_path_var"]}', rel_path)
        nested_set(
            input_dict,
            ["Printing", "OutputFile"],
            rel_path
        )
        
        rel_path = os.path.join(source, template["material_file"]).split(
                os.path.join("resources", os.path.sep))[-1]
        rel_path = os.path.join(f'{settings["exaca"]["case_path_var"]}', 
                                "resources","exaca","template", rel_path)
        nested_set(
            input_dict,
            ["MaterialFileName"],
            rel_path
        )

        # Set path to ExaCA install, which has a copy of the orientation file
        rel_path = os.path.join(f'{settings["exaca"]["exaca_path_var"]}', 
                                "share", "ExaCA",
                                template["orientation_file"])
        nested_set(
            input_dict,
            ["GrainOrientationFile"],
            rel_path
        )

        # Specify the paths to the openfoam temperature data
        rve_dirs = settings["autofoam"]["results"]
        dirs = []
        for d in rve_dirs:
            pn = os.path.basename(d).split("_")[0]
            pn = int(pn.replace("P", ""))
            for part in settings["3DThesis"]["parts"]:
                if part["part_number"] == pn:
                    for i in range(part["layer_start"], part["layer_end"]+1):
                        dirs.append(os.path.join(d, str(i)))
                    break
                else:
                    continue
        dataname = settings["exaca"]["additivefoam_export_name"]
        paths = []
        for d in dirs:
            rel_path = os.path.join(d, dataname).split("results" + os.path.sep)[-1]
            rel_path = os.path.join(f'{settings["exaca"]["case_path_var"]}', rel_path)
            paths.append(rel_path)
    
        nested_set(
            input_dict,
            ["TemperatureData", "TemperatureFiles"],
            paths
        )
        
        with open(target_input, 'w') as f:
            json.dump(input_dict, f, indent=2)
        
    return exaca_cases