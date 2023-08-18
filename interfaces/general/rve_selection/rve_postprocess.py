import argparse
import sys
import os
import pandas as pd
from myna.workflow.load_input import load_input
import numpy as np
import yaml

def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(description='Update Myna input file with region info')
    parser.add_argument('--input', type=str,
                        help='path to the desired input file to run' + 
                        ', for example: ' + 
                        '--input demo.yaml')

    # Parse cmd arguements
    args = parser.parse_args(argv)
    input_file = args.input

    # Get settings
    settings = load_input(input_file)

    # Get RVE file data
    keys = [list(x.keys())[0] for x in settings["steps"]]
    index = keys.index("rve")
    rve_file = os.path.join("results", "rve", settings["steps"][index]["rve"]["output_template"])
    df = pd.read_csv(rve_file, dtype={
        "id":np.int64, 
        "x (m)":np.float64, 
        "y (m)":np.float64, 
        "layer_starts":np.int64, 
        "layer_ends":np.int64,
        "part_number":np.int64})

    # Set up regions dict if it doesn't exist
    for part in settings["data"]["parts"]:
        values = settings["data"]["parts"][part].get("regions")
        if values is None: settings["data"]["parts"][part]["regions"] = {}

    # Use itertuples to iterate while preserving dtype for all columns
    # Note: using iterrows creates a pd.Series, which only has one dtype for all values
    for row in df.itertuples(index=False):
        part = f'P{row.part_number}'
        region = f'rve_{row.id}'
        settings["data"]["parts"][part]["regions"][region] = {
            "X (m)": row._1,
            "Y (m)": row._2,
            "layer_starts": row.layer_starts,
            "layer_ends": row.layer_ends}

    with open(input_file, "w") as f:
        yaml.dump(settings, f, sort_keys=False, default_flow_style=None)

if __name__ == "__main__":
    main(sys.argv[1:])