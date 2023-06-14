import autofoam
import autofoam.mesh
import autofoam.cases
import autofoam.util
import autofoam_case_gen
import os
import pandas as pd
import numpy as np
import json
import shutil

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
    os.makedirs(inputs["case_dir"], exist_ok=True)
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
                 -rs[2]],
                [row["x (m)"] + 0.5*rs[0],
                 row["y (m)"] + 0.5*rs[1],
                 0.0]
            ]
        }

    # Check OpenFOAM install status
    status, msg = autofoam.util.check_openfoam_install_status()

    if generate_cases and status:
        autofoam_case_gen.generate(inputs)
    else:
        # Modify file paths
        inp = inputs.copy()
        inp["mesh"]["stl_path"] = os.path.join(
            ".",
            inp["mesh"]["stl_path"]
        )
        inp["template"]["template_dir"] = os.path.join(
            ".",
            inp["template"]["template_dir"]
        )
        inp["case_dir"] = "."
        inp["input_dir"] = "."
        for case in inp["cases"]:
            path = inp["cases"][case]["scan_path"]
            path = path.split("resources" + os.path.sep)[-1]
            path = os.path.join(".", "resources", path)
            inp["cases"][case]["scan_path"] = path

        # Output inputs as JSON file to case dir
        autofoam_input_file = os.path.join(inputs["case_dir"],
                                           "autofoam_inputs.json")
        with open(autofoam_input_file, 'w') as f:
            json.dump(inp, f, indent=3)

        # Copy case generation script to case dir
        script_src = "autofoam_case_gen.py"
        script_dst = os.path.join(inputs["case_dir"], os.path.basename(script_src))
        shutil.copyfile(script_src, script_dst)

        # Copy case generation readme to case dir
        readme_src = os.path.join("resources", "autofoam", "case_gen_readme.md")
        readme_dst = os.path.join(inputs["case_dir"], os.path.basename(readme_src))
        shutil.copyfile(readme_src, readme_dst)
    
    cases = inputs["cases"].copy()
    case_names = cases.keys()
    case_dirs = []
    # case_dirs = [os.path.join(inputs["input_dir"], inputs["case_dir"], x) for x in case_names]
    for case_name in case_names:
        case_name_alt = "additivefoam"
        part_number = case_name.split("_")[0].split("P")[-1]
        rve_number = case_name.split("_")[-1]
        case_dirs.append(os.path.join(
            inputs["input_dir"],
            inputs["case_dir"], 
            f"P{part_number}", 
            f"rve_{rve_number}", 
            case_name_alt))
    
    return case_dirs