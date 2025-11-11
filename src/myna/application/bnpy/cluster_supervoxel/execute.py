#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import os
import glob
import pandas as pd
import polars as pl
import numpy as np
from myna.core.workflow.load_input import load_input
import matplotlib.pyplot as plt
import myna.application.bnpy as myna_bnpy
from myna.application.bnpy import Bnpy
from myna.application.bnpy import (
    add_cluster_colormap_colorbar,
    get_scatter_marker_size,
)


def reduce_voxel_file_to_supervoxel_df(
    voxel_file,
    app,
    write_csv=False,
    output_file="supervoxel_composition.csv",
):

    # Load voxel cluster data
    df = pl.read_csv(voxel_file)

    # Generate supervoxel locations
    supervoxel_step = app.args.res
    x_min = df.select(pl.col("x (m)")).min().item() + 0.5 * supervoxel_step
    x_max = df.select(pl.col("x (m)")).max().item()
    y_min = df.select(pl.col("y (m)")).min().item() + 0.5 * supervoxel_step
    y_max = df.select(pl.col("y (m)")).max().item()
    supervoxels_xs = np.arange(x_min, x_max, supervoxel_step)
    supervoxels_ys = np.arange(y_min, y_max, supervoxel_step)

    # Assign supervoxel ij-indices for each row
    i = np.argmin(
        np.abs(df.select(pl.col("x (m)")).to_numpy() - supervoxels_xs), axis=1
    )
    j = np.argmin(
        np.abs(df.select(pl.col("y (m)")).to_numpy() - supervoxels_ys), axis=1
    )
    df = df.with_columns(pl.Series(values=i, name="i"))
    df = df.with_columns(pl.Series(values=j, name="j"))
    df = df.sort(["i", "j"])
    ids = [x for x in range(0, app.n_voxel_clusters)]

    # Create new columns for composition
    drop_cols = []
    comp_cols = []
    for id in ids:
        df = df.with_columns((pl.col("id") == id).alias(f"is_{id}"))
        drop_cols.append(f"is_{id}")
        df = df.with_columns((pl.col(f"id").count().over("i", "j")).alias("count"))
        drop_cols.append("count")
        df = df.with_columns(
            ((pl.col(f"is_{id}").sum().over("i", "j")) / (pl.col(f"count")))
            .log10()
            .replace([float("inf"), float("-inf")], 0)
            .alias(f"c_{id}")
        )
        comp_cols.append(f"c_{id}")

    # Filter out any supervoxels with less than the median cell count (removes
    # supervoxels on edge of the part that have only partially melted cells)
    df = df.filter(pl.col("count") >= df["count"].mean())

    # Drop specified columns
    df = df.drop(drop_cols)

    # Get only one row per supervoxel
    df_supervoxel = (
        df.group_by(["i", "j"])
        .agg(*[pl.col(col).mean() for col in comp_cols])
        .sort(["i", "j"])
    )
    xs = supervoxels_xs[df_supervoxel["i"]]
    ys = supervoxels_xs[df_supervoxel["j"]]
    df_supervoxel = df_supervoxel.with_columns(pl.Series(values=xs, name="x (m)"))
    df_supervoxel = df_supervoxel.with_columns(pl.Series(values=ys, name="y (m)"))
    df_supervoxel = df_supervoxel.drop(["i", "j"])
    if write_csv:
        df_supervoxel.write_csv(output_file)

    return df_supervoxel


def train_supervoxel_model(
    myna_files, myna_voxel_files, app, comp_file_name="supervoxel_composition.csv"
):
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
    col_names = [f"c_{x}" for x in range(app.n_voxel_clusters)]
    schema = {}
    for col in col_names:
        schema[col] = float
    df_training = pl.DataFrame(schema=schema)

    # Add training data from each thermal file
    composition_files = []
    supervoxel_step = app.args.res
    for myna_file, myna_voxel_file in zip(myna_files, myna_voxel_files):

        # Get case myna_data
        case_dir = os.path.dirname(myna_file)
        os.chdir(case_dir)
        myna_data = load_input(os.path.join(case_dir, "myna_data.yaml"))

        # Generate case information from myna_data
        build = myna_data["build"]["name"]
        part = list(myna_data["build"]["parts"].keys())[0]
        part_dict = myna_data["build"]["parts"][part]
        layer = list(part_dict["layer_data"].keys())[0]
        layer_dict = part_dict["layer_data"][layer]

        # Create symbolic links to all available clustering results
        voxel_dir = "voxel_data"
        os.makedirs(voxel_dir, exist_ok=True)
        copy_path = os.path.join(voxel_dir, os.path.basename(myna_voxel_file))
        if not os.path.exists(copy_path):
            os.symlink(myna_voxel_file, copy_path)

        # Set output file
        composition_file = os.path.join(case_dir, comp_file_name)

        # Load voxel information
        df_voxel = pl.read_csv(myna_voxel_file)
        df_composition = reduce_voxel_file_to_supervoxel_df(
            myna_voxel_file,
            app,
            write_csv=True,
            output_file=composition_file,
        )
        composition_files.append(composition_file)

        # Remove spatial information for training
        df_case_training = df_composition.drop(["x (m)", "y (m)"])
        df_training = df_training.vstack(df_case_training)

    # Check for other preexitsting training data to include
    suffix_training = "training.csv"
    existing_training_data = sorted(
        glob.glob(os.path.join(app.training_dir, f"*{suffix_training}"))
    )
    for datafile in existing_training_data:
        df_temp = pl.read_csv(datafile)
        df_training = df_training.vstack(df_temp)

    # Drop any exact duplicates to avoid overpopulation of training dataset
    df_training = df_training.unique()

    # Save the assembled training dataset
    prefix = "data"
    n_training = (
        len(glob.glob(os.path.join(app.training_dir, f"*{suffix_training}"))) + 1
    )  # model numbers are 1-indexed for bnpy
    training_datafile = os.path.join(
        app.training_dir, f"{prefix}_{n_training}_{suffix_training}"
    )
    df_training.write_csv(training_datafile)

    # Drop any clusters with compositions < 0.01 to avoid sparse dataspace
    filter_supervoxel_comp_df(df_training)

    # Convert the whole dataset to a bnpy dataset for clustering after model training
    df_pandas = pd.DataFrame(data=df_training.to_numpy(), columns=df_training.columns)
    dataset = bnpy.data.XData.from_dataframe(df_pandas)

    # Train the model
    model_dir = app.get_model_dir_path()
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
            sF=app.sF,
            gamma=app.gamma,
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
        latest_model_iteration = app.get_latest_model_path()
        model_num = int(os.path.dirname(latest_model_iteration).split(os.sep)[-1])
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
            sF=app.sF,
            gamma=app.gamma,
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

    # Return to original working directory and return result file path
    os.chdir(orig_dir)
    return trained_model_path, composition_files


def filter_supervoxel_comp_df(df):
    cols = df.columns
    for col in cols:
        if df.select(pl.col(col)).max().item() < -2:
            df = df.drop(col)
    return


def run(
    myna_file,
    composition_file,
    model_path,
    app,
):
    """Generate supervoxel training data from the voxel clustering data"""

    # Load app-specific dependencies
    try:
        import bnpy
    except ImportError:
        raise ImportError(
            'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
        )

    # Store original working directory
    orig_dir = os.getcwd()

    # Create bnpy dataset for clustering
    df = pl.read_csv(composition_file)
    df_composition = df.drop("x (m)", "y (m)")
    filter_supervoxel_comp_df(df_composition)
    df_pandas = pd.DataFrame(
        data=df_composition.to_numpy(), columns=df_composition.columns
    )
    dataset = bnpy.data.XData.from_dataframe(df_pandas)
    df = pd.DataFrame(data=df.to_numpy(), columns=df.columns)

    # Assign cluster IDs and write Myna output file, overwriting if specified
    # If there is uncertainty (certainty between top two clusters < 10%), then
    # use the more populous cluster (lower cluster number)
    cur_model, _ = bnpy.load_model_at_lap(model_path, None)
    if not os.path.exists(myna_file) or app.args.overwrite:
        local_params = cur_model.calc_local_params(dataset)
        resp = local_params["resp"]
        soft_cluster = np.argmax(resp, axis=1)
        n_supervoxel_clusters = cur_model.allocModel.K
        df["id"] = soft_cluster
        df.to_csv(myna_file, index=False)

        # Scatter plot of supervoxel cluster IDs
        colors, cmap, colorValues = myna_bnpy.cluster_colormap(
            n_supervoxel_clusters, colorspace="tab10"
        )
        dpi = 150
        fig, ax = plt.subplots(dpi=dpi, figsize=(7, 5))
        pad = 1e-3
        x_min = df["x (m)"].min() - pad
        x_max = df["x (m)"].max() + pad
        y_min = df["y (m)"].min() - pad
        y_max = df["y (m)"].max() + pad
        ax.scatter(
            [x_min, x_min, x_max, x_max],
            [y_min, y_max, y_min, y_max],
            color="white",
            marker="+",
        )
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        add_cluster_colormap_colorbar(fig, ax, colors, cmap, n_supervoxel_clusters)
        ax.set_aspect(1)
        plt.tight_layout()
        ax.scatter(
            df["x (m)"],
            df["y (m)"],
            c=df["id"],
            cmap=cmap,
            s=get_scatter_marker_size(fig, ax, app.args.res),
            marker="s",
        )
        export_file = os.path.join(
            os.path.dirname(myna_file), "supervoxel_cluster_id.png"
        )
        plt.savefig(export_file)
        plt.close()

        # Scatter plot of supervoxel compositions
        if app.n_voxel_clusters > 3:
            nrows = int(np.ceil(app.n_voxel_clusters / 3))
        else:
            nrows = 1
        df_linear = df.replace(0, np.nan)
        for col in df_linear.columns:
            df_linear[col] = np.power(10, df_linear[col])
        myna_bnpy.combined_supervoxel_composition_scatter(
            df_linear,
            app.n_voxel_clusters,
            app.args.res,
            nrows=nrows,
            ncols=3,
            dpi=150,
            export_name=composition_file.replace(".csv", ".png"),
        )

    os.chdir(orig_dir)
    return


def main():

    app = Bnpy("cluster_supervoxel")

    # Set up argparse
    parser = app.parser
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

    # Parse command line arguments
    app.args = parser.parse_args()

    try:
        import bnpy
    except ImportError:
        raise ImportError(
            'Myna bnpy app requires "pip install .[bnpy]" optional dependencies!'
        )

    # Get latest voxel model
    voxel_model_path = app.args.voxel_model
    voxel_model_path = voxel_model_path.replace("/", os.sep)
    voxel_model_path = sorted(
        glob.glob(os.path.join(voxel_model_path, "*")), reverse=True
    )[
        0
    ]  # Model iteration
    voxel_model_path = sorted(
        glob.glob(os.path.join(voxel_model_path, "*")), reverse=True
    )[
        0
    ]  # Training iteration
    voxel_model, lap_val = bnpy.load_model_at_lap(voxel_model_path, None)
    app.n_voxel_clusters = max(voxel_model.allocModel.K, 2)

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = app.settings["data"]["output_paths"][step_name]
    cluster_step_name = app.args.cluster
    if cluster_step_name == "":
        cluster_step_name = os.environ["MYNA_LAST_STEP_NAME"]
    voxel_cluster_files = app.settings["data"]["output_paths"][cluster_step_name]

    # Assemble training data and train model
    supervoxel_composition_filename = "supervoxel_composition.csv"
    app.sF = 0.5
    app.gamma = 8.0
    if app.args.train_model:
        trained_model_path, composition_files = train_supervoxel_model(
            myna_files,
            voxel_cluster_files,
            app,
            comp_file_name=supervoxel_composition_filename,
        )
    else:
        trained_model_path = app.get_latest_model_path()
        composition_files = [
            os.path.join(os.path.dirname(myna_file), supervoxel_composition_filename)
            for myna_file in myna_files
        ]
        pass

    # Run clustering on supervoxel compositions
    print("- Clustering supervoxel data:")
    for myna_file, composition_file in zip(myna_files, composition_files):
        print(f"  - {composition_file=}")
        run(
            myna_file,
            composition_file,
            trained_model_path,
            app,
        )


if __name__ == "__main__":
    main()
