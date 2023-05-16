import autofoam
import autofoam.mesh
import autofoam.cases
import autofoam.util
import os

def run_autofoam(settings, generate_cases=True):
    inputs = settings["autofoam"]
    inputs["input_dir"] = os.path.dirname(os.path.realpath(__file__))
    print("Input directory: ", inputs["input_dir"])

    if generate_cases:
        # Preprocess STL
        working_stl_path = autofoam.mesh.preprocess_stl(inputs)

        # Generate AdditiveFOAM mesh features
        origin, bbDict = autofoam.mesh.create_background_mesh(inputs, working_stl_path)
        autofoam.mesh.extract_stl_features(inputs, origin)

        # Create mesh
        autofoam.mesh.creat_part_mesh(inputs, bbDict)

        # Create case files
        autofoam.cases.create_case_files(inputs)
    
    cases = inputs["cases"].copy()
    cases.pop("case_dir")
    case_names = cases.keys()
    case_dirs = [os.path.join(inputs["input_dir"], inputs["cases"]["case_dir"], x) for x in case_names]
    
    return case_dirs