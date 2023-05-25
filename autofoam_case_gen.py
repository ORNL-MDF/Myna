import autofoam
import json

def generate(inputs):
    # Preprocess STL
    working_stl_path = autofoam.mesh.preprocess_stl(inputs)

    # Generate AdditiveFOAM mesh features
    origin, bbDict = autofoam.mesh.create_background_mesh(inputs, working_stl_path)
    autofoam.mesh.extract_stl_features(inputs, origin)

    # Create mesh
    autofoam.mesh.creat_part_mesh(inputs, bbDict)

    # Create case files
    autofoam.cases.create_case_files(inputs)



if __name__ == "__main__":
    with open("autofoam_inputs.json", "r") as f:
        inputs = json.load(f)

    generate(inputs)