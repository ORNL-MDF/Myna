#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import pandas as pd
import numpy as np
from myna.core.workflow.load_input import load_input
import myna.application.bnpy as myna_bnpy
import sys
import glob
import matplotlib.pyplot as plt
from myna.application.bnpy import Bnpy, get_representative_distribution


def reduce_thermal_file_to_df(thermal_file):
    # Reduce data file to necessary columns
    df_reduced = pd.read_csv(thermal_file)
    new_cols = {}
    for col in df_reduced.columns:
        new_cols[col] = col.lower()
    df_reduced.rename(columns=new_cols, inplace=True)
    df_reduced["logG"] = np.log10(df_reduced["g (k/m)"])
    df_reduced["logV"] = np.log10(df_reduced["v (m/s)"])
    df_reduced.drop(columns=["g (k/m)", "v (m/s)"], inplace=True)

    # Remove any nan or inf
    df_reduced = df_reduced[np.isfinite(df_reduced).all(1)]

    # Get correct columns for training data
    keep_cols = ["logG", "logV"]
    drop_cols = []
    for col in df_reduced.columns:
        if col not in keep_cols:
            drop_cols.append(col)
    df_training = df_reduced.drop(columns=drop_cols)

    return df_reduced, df_training


def train_voxel_model(myna_files, thermal_files, sF, gamma, input_dir):
    # Load app-specific dependencies
    try:
        import bnpy
    except ImportError:
        raise ImportError(
            'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
        )

    # Store original working directory
    orig_dir = os.getcwd()

    # Create blank dataframe
    df_training = pd.DataFrame({"logG": [], "logV": []})

    # Add training data from each thermal file
    for myna_file, thermal_file in zip(myna_files, thermal_files):

        # Go to case directory
        case_dir = os.path.dirname(myna_file)
        os.chdir(case_dir)

        # Get case myna_data
        myna_data = load_input(os.path.join(case_dir, "myna_data.yaml"))
        resource_dir = os.path.join(input_dir, "myna_resources")

        # Generate case information from myna_data
        build = myna_data["build"]["name"]
        part = list(myna_data["build"]["parts"].keys())[0]
        part_dict = myna_data["build"]["parts"][part]
        layer = list(part_dict["layer_data"].keys())[0]
        layer_dict = part_dict["layer_data"][layer]

        # Set directory for training data
        resource_template_dir = os.path.join(resource_dir, "cluster_solidification")

        # Create symbolic links to all available thermal results
        thermal_dir = "thermal_data"
        os.makedirs(thermal_dir, exist_ok=True)
        copy_path = os.path.join("thermal_data", os.path.basename(thermal_file))
        if not os.path.exists(copy_path):
            try:
                os.symlink(thermal_file, copy_path)
            except FileExistsError:
                os.remove(copy_path)
                os.symlink(thermal_file, copy_path)
        thermal_file_local = copy_path

        # Set up folder structure
        training_dir = os.path.join(resource_template_dir, "training_voxels")
        os.makedirs(training_dir, exist_ok=True)

        # Reduce data to only the columns needed for training
        _, df_case_training = reduce_thermal_file_to_df(thermal_file_local)

        # Get a representative sampling of the case dataset
        training_data, _ = get_representative_distribution(
            df_case_training.to_numpy(), bins=20
        )
        df_case_training = pd.DataFrame(
            data=training_data, columns=df_case_training.columns
        )

        # Concatenate the case data to the training dataset
        df_training = pd.concat([df_training, df_case_training], ignore_index=True)

    # Get a representative sampling of the training dataset for the current cases
    training_data, _ = get_representative_distribution(df_training.to_numpy(), bins=20)
    df_training = pd.DataFrame(data=training_data, columns=df_training.columns)

    # Check for other preexitsting training data to include
    suffix_training = "training.csv"
    existing_training_data = sorted(
        glob.glob(os.path.join(training_dir, f"*{suffix_training}"))
    )
    for datafile in existing_training_data:
        df_temp = pd.read_csv(datafile)
        df_training = pd.concat([df_training, df_temp], ignore_index=True)

    # Get representative distribution of the entire training dataset
    training_data, _ = get_representative_distribution(df_training.to_numpy(), bins=20)
    df_training = pd.DataFrame(data=training_data, columns=df_training.columns)

    # Save the assembled training dataset
    prefix = "data"
    n_training = (
        len(glob.glob(os.path.join(training_dir, f"*{suffix_training}"))) + 1
    )  # model numbers are 1-indexed for bnpy
    training_datafile = os.path.join(
        training_dir, f"{prefix}_{n_training}_{suffix_training}"
    )
    df_training.to_csv(training_datafile, index=False)

    # Load the complete training dataframe to bnpy dataset
    dataset = bnpy.data.XData.from_dataframe(df_training)

    # Train the model
    model_dir = os.path.join(
        resource_template_dir, f"voxel_model-sF={sF}-gamma={gamma}"
    )
    if not os.path.isdir(model_dir):
        _, info_dict = bnpy.run(
            dataset,
            "DPMixtureModel",
            "Gauss",
            "memoVB",
            output_path=os.path.join(model_dir, "1"),
            nLap=5000,
            nTask=1,
            nBatch=10,
            convergeThr=0.001,
            sF=sF,
            gamma=gamma,
            ECovMat="eye",
            K=20,
            initname="randexamplesbydist",
            moves="birth,merge,shuffle",
            m_startLap=5,
            b_startLap=2,
            b_Kfresh=4,
        )

        print(f'{info_dict["task_output_path"]=}')
        trained_model_path = info_dict["task_output_path"]

    else:
        latest_model = sorted(glob.glob(os.path.join(model_dir, "*")), reverse=True)[0]
        latest_model_iteration = sorted(
            glob.glob(os.path.join(latest_model, "*")), reverse=True
        )[0]
        model_num = int(latest_model.split(os.sep)[-1])

        latest_model_obj, _ = bnpy.load_model_at_lap(latest_model_iteration, None)
        previous_K = latest_model_obj.obsModel.K

        _, info_dict = bnpy.run(
            dataset,
            "DPMixtureModel",
            "Gauss",
            "memoVB",
            output_path=os.path.join(model_dir, f"{model_num + 1}"),
            nLap=5000,
            nTask=1,
            nBatch=10,
            convergeThr=0.001,
            sF=sF,
            gamma=gamma,
            ECovMat="eye",
            K=previous_K,
            initname=latest_model_iteration,
            moves="birth,merge,shuffle",
            m_startLap=5,
            b_startLap=2,
            b_Kfresh=4,
        )

        print(f'{info_dict["task_output_path"]=}')
        trained_model_path = info_dict["task_output_path"]

    # Return to original working directory
    os.chdir(orig_dir)

    return trained_model_path


def run_clustering(
    case_dir,
    thermal_file,
    sF,
    gamma,
    overwrite,
    input_dir,
):
    # Load app-specific dependencies
    try:
        import bnpy
    except ImportError:
        raise ImportError(
            'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
        )

    # Go to case directory
    orig_dir = os.getcwd()
    os.chdir(case_dir)

    # Get case myna_data
    myna_data = load_input(os.path.join(case_dir, "myna_data.yaml"))
    resource_dir = os.path.join(input_dir, "myna_resources")

    # Generate case information from myna_data
    build = myna_data["build"]["name"]
    part = list(myna_data["build"]["parts"].keys())[0]
    part_dict = myna_data["build"]["parts"][part]
    layer = list(part_dict["layer_data"].keys())[0]
    layer_dict = part_dict["layer_data"][layer]

    # Set directory for training data
    resource_template_dir = os.path.join(resource_dir, "cluster_solidification")

    # Create symbolic links to all available thermal results
    thermal_dir = "thermal_data"
    os.makedirs(thermal_dir, exist_ok=True)
    copy_path = os.path.join("thermal_data", os.path.basename(thermal_file))
    if not os.path.exists(copy_path):
        try:
            os.symlink(thermal_file, copy_path)
        except FileExistsError:
            os.remove(copy_path)
            os.symlink(thermal_file, copy_path)
    thermal_file_local = copy_path

    # Set up folder structure for voxel clustering results
    cluster_dir = os.path.join(case_dir, "cluster_voxels")
    os.makedirs(cluster_dir, exist_ok=True)

    # Convert the thermal dataset to a bnpy dataset for clustering
    df_output, df_cluster = reduce_thermal_file_to_df(thermal_file_local)
    dataset_current = bnpy.data.XData.from_dataframe(df_cluster)

    # Get the latest trained model
    model_dir = os.path.join(
        resource_template_dir, f"voxel_model-sF={sF}-gamma={gamma}"
    )
    latest_model = sorted(glob.glob(os.path.join(model_dir, "*")), reverse=True)[0]
    latest_model_iteration = sorted(
        glob.glob(os.path.join(latest_model, "*")), reverse=True
    )[0]
    task_output_path = latest_model_iteration
    model_num = int(latest_model.split(os.sep)[-1])
    cur_model, lap_val = bnpy.load_model_at_lap(task_output_path, None)

    # Assign cluster IDs, or overwrite them if specified
    result_file = os.path.join(cluster_dir, f"cluster_ids.csv")
    if not os.path.exists(result_file) or overwrite:
        compIDs = np.arange(0, cur_model.obsModel.K)
        if cur_model.allocModel.K == cur_model.obsModel.K:
            w = cur_model.allocModel.get_active_comp_probs()
        else:
            w = np.ones(cur_model.obsModel.K)
        K = cur_model.allocModel.K

        # Assign current data to clusters
        local_params = cur_model.calc_local_params(dataset_current)
        resp = local_params["resp"]
        soft_cluster = np.argmax(resp, axis=1)
        n_digits = cur_model.allocModel.K
        df_output["id"] = soft_cluster
        df_output.to_csv(result_file, index=False)

    # If file already exists and should not be overwritten, load cluster IDs
    else:
        df_output = pd.read_csv(result_file)
        n_digits = cur_model.allocModel.K
        K = n_digits

    # Generate plots
    dpi = 300
    colors, cmap, _ = myna_bnpy.cluster_colormap(n_digits)
    suffix = f"sF={sF}-g={gamma}-K={K}"

    # GV plot
    gv_plot_file = os.path.join(cluster_dir, f"cluster_GV-{suffix}.png")
    if not os.path.exists(gv_plot_file) or overwrite:
        myna_bnpy.voxel_GV_plot(df_output, colors, cmap, gv_plot_file, dpi=dpi)

    # Field histograms
    fields = ["logG", "logV"]
    for field in fields:
        field_value_file = os.path.join(cluster_dir, f"cluster_{field}-{suffix}.png")
        if not os.path.exists(field_value_file) or overwrite:
            myna_bnpy.voxel_id_stacked_histogram(
                df_output,
                field,
                colors,
                field_value_file,
                dpi=dpi,
                ids=[x for x in range(K)],
            )

    # Spatial map of clusters
    map_plot_file = os.path.join(cluster_dir, f"cluster_map-{suffix}.png")
    if not os.path.exists(map_plot_file) or overwrite:
        plt.figure(dpi=dpi)
        colormap = "tab10"
        if n_digits > 10:
            colormap = "tab20"
        colors, cmap, colorValues = myna_bnpy.cluster_colormap(
            n_digits, colorspace=colormap
        )
        fig, ax = plt.subplots()
        ax.scatter(
            df_output["x (m)"] * 1e3,
            df_output["y (m)"] * 1e3,
            c=df_output["id"],
            s=1,
            marker="s",
            cmap=cmap,
        )
        ax.set_aspect("equal")
        ax.set_xlabel("X (mm)")
        ax.set_ylabel("Y (mm)")
        plt.savefig(map_plot_file, dpi=dpi)
        plt.close()

    # Return to original working directory and return result file path
    os.chdir(orig_dir)
    return result_file


def main():
    app = Bnpy("cluster_solidification")

    # Set up argparse
    parser = app.parser
    parser.add_argument(
        "--thermal",
        default=None,
        type=str,
        help='thermal step name, for example: "--thermal 3dthesis"',
    )

    # Parse command line arguments
    args = parser.parse_args()
    settings = load_input(os.environ["MYNA_INPUT"])
    train_model = args.train_model
    overwrite = args.overwrite

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]
    thermal_step_name = args.thermal
    if thermal_step_name is None:
        thermal_step_name = os.environ["MYNA_LAST_STEP_NAME"]
    thermal_files = settings["data"]["output_paths"][thermal_step_name]

    # Assemble training data and train model
    gamma = 8
    sF = 0.5
    if train_model:
        train_voxel_model(
            myna_files, thermal_files, sF, gamma, os.path.dirname(app.input_file)
        )

    # Run clustering using trained model
    output_files = []
    for case_dir, thermal_file in zip(
        [os.path.dirname(x) for x in myna_files], thermal_files
    ):
        print("Running clustering for:")
        print(f"- {case_dir=}")
        print(f"- {thermal_file=}")
        output_files.append(
            run_clustering(case_dir, thermal_file, sF, gamma, overwrite, app)
        )

    # Post-process results to convert to Myna format
    for filepath, mynafile in zip(output_files, myna_files):
        df = pd.read_csv(filepath)
        df.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main()
