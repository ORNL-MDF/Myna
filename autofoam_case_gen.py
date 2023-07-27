import autofoam
import autofoam.mesh
import autofoam.cases
import json
import os

def nested_set(dict, keys, value):
    ''' modifies a nested dictionary value given a list of keys to the nested location'''
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    dict[keys[-1]] = value

def nested_get(dict, keys):
    ''' modifies a nested dictionary value given a list of keys to the nested location'''
    for key in keys[:-1]:
        dict = dict.setdefault(key, {})
    return dict[keys[-1]]

def generate(inputs):
    # Preprocess STL
    working_stl_path = autofoam.mesh.preprocess_stl(inputs)

    # Generate AdditiveFOAM mesh features
    origin, bbDict = autofoam.mesh.create_background_mesh(inputs, working_stl_path)
    autofoam.mesh.extract_stl_features(inputs, origin)

    # Create mesh
    autofoam.mesh.create_part_mesh(inputs, bbDict)

    # Create case files
    inp = inputs.copy()
    cases = inputs["cases"]
    for case_name, case in cases.items():
        case_name_alt = "additivefoam"
        part_number = case_name.split("_")[0].split("P")[-1]
        rve_number = case_name.split("_")[-1]
        inp["case_dir"] = os.path.join(inputs["case_dir"], f"P{part_number}", f"rve_{rve_number}")
        inp["cases"] = {case_name_alt: case}
        autofoam.cases.create_case(inp, case_name_alt, os.path.abspath(os.path.join(inp["case_dir"], case_name_alt)))

if __name__ == "__main__":

    with open("autofoam_inputs.json", "r") as f:
        inputs = json.load(f)

    path_inputs = [
        ["mesh","stl_path"],
        ["template","template_dir"],
        ["case_dir"]]
    
    # Set the path for input directories
    for path_input in path_inputs:
        path = nested_get(inputs, path_input)
        if not os.path.isabs(path):
            new_path = os.path.abspath(path)
            nested_set(inputs, path_input, new_path)
            print(path, new_path)
    
    # For each case update the relevant paths
    for case in inputs["cases"].keys():
        print(case)
        case_path = inputs["cases"][case]["scan_path"]
        path_input = ["cases", case, "scan_path"]
        if not os.path.isabs(case_path):
            new_path = os.path.abspath(case_path)
            nested_set(inputs, path_input, new_path)
            print(case_path, new_path)

    with open("autofoam_inputs_abs.json", "w") as f:
        json.dump(inputs, f, indent=3)

    generate(inputs)