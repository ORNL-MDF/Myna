import autofoam
import autofoam.mesh
import autofoam.cases
import autofoam.util
import os
import pandas as pd
import numpy as np

def get_rve_locs(rve_file, buildmeta_file):

    rve_df = pd.read_csv(rve_file)
    meta = np.load(buildmeta_file)
    rve_df["layer_thickness"] = meta["layer_thickness"]*1e-3
    rve_df["z_start"] = rve_df["layer_thickness"] * rve_df["layer_starts"]
    rve_df["z_end"] = rve_df["layer_thickness"] * rve_df["layer_ends"]
    rve_df["z (m)"] = 0.5*(rve_df["z_end"] - rve_df["z_start"])
    
    return rve_df

def run_autofoam(settings, generate_cases=True):
    inputs = settings["autofoam"]
    inputs["input_dir"] = os.path.dirname(os.path.realpath(__file__))
    print("Input directory: ", inputs["input_dir"])

    # Generate case information from RVE list
    inputs["cases"] = {}
    buildmeta = os.path.join(settings["Peregrine"]["build_path"], 
                             "simulation", 
                             "buildmeta.npz")
    rve_df = get_rve_locs(settings["rve"]["results"], buildmeta)
    rs = settings["autofoam"]["rve_size"]
    for index, row in rve_df.iterrows():
        pn = int(row["part_number"])
        inputs["cases"][f'P{pn:d}_rve_{int(row["id"]):d}'] = {
            "scan_path":os.path.join(settings["Peregrine"]["build_path"],
                                      "simulation",
                                      f'P{pn:d}'),
            "layers":[x for x in range(int(row["layer_starts"]), int(row["layer_ends"] + 1))],
            "heights":[row["z_start"], row["z_end"]],
            "RVE":[
                [row["x (m)"] - 0.5*rs[0],
                 row["y (m)"] - 0.5*rs[1],
                 row["z_end"] - rs[2]],
                [row["x (m)"] + 0.5*rs[0],
                 row["y (m)"] + 0.5*rs[1],
                 row["z_end"]]
            ]
        }

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
    case_names = cases.keys()
    case_dirs = [os.path.join(inputs["input_dir"], inputs["case_dir"], x) for x in case_names]
    
    return case_dirs