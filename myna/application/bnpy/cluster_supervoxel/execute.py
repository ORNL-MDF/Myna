import os
import sys
import glob
import bnpy
import argparse
import pandas as pd
import numpy as np
from myna.core.workflow.load_input import load_input
import myna.application.bnpy as myna_bnpy


def run(
    case_dir,
    cluster_file,
    settings,
    train_model,
    overwrite,
    voxel_model_path,
    supervoxelStep=250e-6,
    dpi=300,
):
    """Generate supervoxel training data from the voxel clustering data"""
    # Go to case directory
    orig_dir = os.getcwd()
    os.chdir(case_dir)

    # Get case myna_data
    myna_data = load_input(os.path.join(case_dir, "myna_data.yaml"))
    input_dir = os.path.dirname(myna_data["myna"]["input"])
    resource_dir = os.path.join(input_dir, "myna_resources")

    # Generate case information from myna_data
    build = myna_data["build"]["name"]
    part = list(myna_data["build"]["parts"].keys())[0]
    part_dict = myna_data["build"]["parts"][part]
    layer = list(part_dict["layer_data"].keys())[0]
    layer_dict = part_dict["layer_data"][layer]

    # Set directory for training data
    resource_template_dir = os.path.join(resource_dir, "cluster_solidification")

    # Load cluster data
    df = pd.read_csv(cluster_file)

    # Assume constant voxel step
    xs = sorted(np.array(df["x (m)"].unique()))
    voxelStep = xs[1] - xs[0]

    # Create mesh object
    xDomain = df["x (m)"]
    yDomain = df["y (m)"]
    step = supervoxelStep
    xmin, xmax = [np.min(xDomain), np.max(xDomain)]
    ymin, ymax = [np.min(yDomain), np.max(yDomain)]
    xrem = (xmax - xmin) % step
    yrem = (ymax - ymin) % step
    xmin, xmax = [xmin - 0.5 * xrem, xmax + 0.5 * xrem]
    ymin, ymax = [ymin - 0.5 * yrem, ymax + 0.5 * yrem]
    nx, ny = [np.round((xmax - xmin) / step) - 1, round((ymax - ymin) / step) - 1]
    xx, yy = np.mgrid[
        xmin + 0.5 * step : xmax - 0.5 * step : nx * 1j,
        ymin + 0.5 * step : ymax - 0.5 * step : ny * 1j,
    ]
    mesh = np.vstack([xx.ravel(), yy.ravel()]).T
    mesh = pd.DataFrame(mesh, columns=["x (m)", "y (m)"])

    # Create symbolic links to all available clustering results
    training_dir = "training_data"
    os.makedirs(training_dir, exist_ok=True)
    copy_path = os.path.join(training_dir, os.path.basename(cluster_file))
    if not os.path.exists(copy_path):
        os.symlink(cluster_file, copy_path)

    # Setup folder structure
    training_dir = os.path.join(resource_template_dir, "training_supervoxels")
    cluster_dir = os.path.join(case_dir, "cluster_supervoxels")
    os.makedirs(training_dir, exist_ok=True)
    os.makedirs(cluster_dir, exist_ok=True)

    # TODO: Load number of clusters from the voxel clustering model,
    # do not expect that any given file will have all the voxel cluster ids
    # that are possible given the voxel clustering model
    #
    # Add a new field to track fraction of points in each mesh grid for each cluster
    clusters = np.arange(0, 10)
    meshCompCSV = os.path.join("supervoxel_composition.csv")

    # TODO: Need to estimate voxelStep from the cluster data or rethink the normalization step
    # TODO: Fix the normalization if steps are not perfectly lined up with supervoxel mesh
    #       (i.e., normalize with consideration for voxel only partially contained in supervoxel)
    # TODO: See if this calculation can be sped up
    #
    # Calculate the supervoxel composition (note that this is VERY slow at the moment)
    if not os.path.exists(meshCompCSV) or overwrite:
        print(f"Dataset {id}: Generating supervoxel compositions...")
        for cluster in clusters:
            mesh[f"comp_{cluster}"] = 0.0
        cell1Area = np.power(voxelStep, 2)
        cell2Area = np.power(supervoxelStep, 2)
        printStep = max(int(0.1 * len(mesh)), 1)
        for index, row in mesh.iterrows():
            if index % printStep == 0:
                print(f"Calculating composition for mesh loc {index+1} of {len(mesh)}")
            dff = df[
                (df["x (m)"].values >= row["x (m)"] - 0.5 * supervoxelStep)
                & (df["x (m)"] <= row["x (m)"] + 0.5 * supervoxelStep)
                & (df["y (m)"] >= row["y (m)"] - 0.5 * supervoxelStep)
                & (df["y (m)"] <= row["y (m)"] + 0.5 * supervoxelStep)
            ]
            for cluster in clusters:
                labelMatch = dff[dff["id"] == cluster]
                count = len(labelMatch)
                if count > 0:
                    fraction = count * cell1Area / cell2Area
                    mesh.at[index, f"comp_{cluster}"] = fraction

        mesh.to_csv(meshCompCSV, index=False)
    else:
        mesh = pd.read_csv(meshCompCSV)

    for cluster in clusters:
        myna_bnpy.cluster_composition_map(
            xx * 1e3,
            yy * 1e3,
            mesh,
            cluster,
            f"composition_map.id_{cluster}.png",
            dpi=dpi,
        )

    # Copy mesh data and remove spatial information
    df_training = mesh.copy()
    df_training.drop(columns=["x (m)", "y (m)"], inplace=True)

    # Plot distribution of values for each variable
    xmin, xmax = [0, 1]
    for col in df_training.columns:
        print(f"Generating histogram for distribution of {col}")
        myna_bnpy.supervoxel_composition_hist(
            df_training, col, exportName=f"training_data_dist-{col}.png", dpi=dpi
        )

    # Convert the whole dataset to a bnpy dataset for clustering after model training
    dataset_current = bnpy.data.XData.from_dataframe(df_training)
    gamma = 8
    sF = 0.5

    # Check if model needs to be trained or not
    model_dir = os.path.join(
        resource_template_dir, f"supervoxel_model-sF={sF}-gamma={gamma}"
    )
    if not train_model and os.path.isdir(model_dir):
        latest_model = sorted(glob.glob(os.path.join(model_dir, "*")), reverse=True)[0]
        latest_model_iteration = sorted(
            glob.glob(os.path.join(latest_model, "*")), reverse=True
        )[0]
        task_output_path = latest_model_iteration

    else:
        suffix_training = "training.csv"
        prefix = "data"
        n_training = (
            len(glob.glob(os.path.join(training_dir, f"*{suffix_training}"))) + 1
        )  # model numbers are 1-indexed for bnpy
        training_datafile = os.path.join(
            training_dir, f"{prefix}_{n_training}_{suffix_training}"
        )
        df_training.to_csv(training_datafile, index=False)

        # Check for other training data and load to training dataset if it exists
        existing_training_data = sorted(
            glob.glob(os.path.join(training_dir, f"*{suffix_training}"))
        )
        for datafile in existing_training_data:
            df_temp = pd.read_csv(datafile)
            df_training = pd.concat([df_training, df_temp], ignore_index=True)

        # Load the complete training dataframe to bnpy dataset
        dataset = bnpy.data.XData.from_dataframe(df_training)
        print(df_training)

        # Train the model
        if not os.path.isdir(model_dir):
            trained_model, info_dict = bnpy.run(
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
            task_output_path = info_dict["task_output_path"]

        else:
            latest_model = sorted(
                glob.glob(os.path.join(model_dir, "*")), reverse=True
            )[0]
            latest_model_iteration = sorted(
                glob.glob(os.path.join(latest_model, "*")), reverse=True
            )[0]
            model_num = int(latest_model.split(os.sep)[-1])

            trained_model, info_dict = bnpy.run(
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
                K=20,
                initname=latest_model_iteration,
                moves="birth,merge,shuffle",
                m_startLap=5,
                b_startLap=2,
                b_Kfresh=4,
            )

            print(f'{info_dict["task_output_path"]=}')
            task_output_path = info_dict["task_output_path"]

    result_file = os.path.join(cluster_dir, f"cluster_ids.csv")
    cur_model, lap_val = bnpy.load_model_at_lap(task_output_path, None)
    df_output = mesh.copy()

    # Assign cluster IDs, or overwrite them if specified
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

    # Generate colormap for supervoxel voxel cluster ID compositions
    voxel_model, lap_val = bnpy.load_model_at_lap(voxel_model_path, None)
    n_digits = max(voxel_model.allocModel.K, 2)
    colors, cmap, colorValues = myna_bnpy.cluster_colormap(n_digits, colorspace="tab10")
    suffix = f"sF={sF}-g={gamma}-K={K}"

    # Plot colormesh of supervoxel cluster IDs
    n_digits = max(cur_model.allocModel.K, 2)
    colors, cmap, colorValues = myna_bnpy.cluster_colormap(n_digits, colorspace="tab10")
    mesh["X(mm)"] = mesh["x (m)"] * 1e3
    mesh["Y(mm)"] = mesh["y (m)"] * 1e3
    mesh["id"] = df_output["id"].to_numpy()
    myna_bnpy.supervoxel_id_colormesh(
        mesh, colorValues, cmap, exportName=f"cluster_supervoxel-{suffix}.png", dpi=dpi
    )

    os.chdir(orig_dir)
    return result_file


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch clustering for " + "specified input file"
    )
    parser.add_argument(
        "--cluster",
        default="",
        type=str,
        help="input cluster step name" + ", for example: " + "--cluster cluster",
    )
    parser.add_argument(
        "--voxel-model",
        dest="voxel_model",
        default="myna_resources/cluster_solidification/voxel_model-sF=0.5-gamma=8",
        type=str,
        help="path to model for voxel clustering",
    )
    parser.add_argument(
        "--res",
        default=250.0e-6,
        type=float,
        help="resolution to use for super-voxel size, in meters"
        + ", for example: "
        + "--res 250.0e-6",
    )
    parser.add_argument(
        "--no-training",
        dest="train_model",
        action="store_false",
        help="flag to use pre-trained clustering model (error will "
        + "be thrown is no clustering model exists)",
    )
    parser.add_argument(
        "--overwrite",
        dest="overwrite",
        action="store_true",
        help="flag to force overwrite of existing cluster IDs",
    )
    parser.set_defaults(train_model=True)
    parser.set_defaults(overwrite=False)

    # Parse command line arguments
    args = parser.parse_args(argv)
    settings = load_input(os.environ["MYNA_RUN_INPUT"])
    train_model = args.train_model
    overwrite = args.overwrite
    resolution = args.res

    # Get latest voxel model
    voxel_model = args.voxel_model
    voxel_model = voxel_model.replace("/", os.sep)
    # Model iteration
    voxel_model = sorted(glob.glob(os.path.join(voxel_model, "*")), reverse=True)[0]
    # Training iteration
    voxel_model = sorted(glob.glob(os.path.join(voxel_model, "*")), reverse=True)[0]

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]
    cluster_step_name = args.cluster
    if cluster_step_name == "":
        cluster_step_name = os.environ["MYNA_LAST_STEP_NAME"]
    cluster_files = settings["data"]["output_paths"][cluster_step_name]

    # Run clustering
    output_files = []
    for case_dir, cluster_file in zip(
        [os.path.dirname(x) for x in myna_files], cluster_files
    ):
        print("Running clustering for:")
        print(f"- {case_dir=}")
        print(f"- {cluster_file=}")
        output_files.append(
            run(
                case_dir,
                cluster_file,
                settings,
                train_model,
                overwrite,
                voxel_model,
                supervoxelStep=resolution,
            )
        )

    # Post-process results to convert to Myna format
    for filepath, mynafile in zip(output_files, myna_files):
        df = pd.read_csv(filepath)
        df.to_csv(mynafile, index=False)


if __name__ == "__main__":
    main(sys.argv[1:])
