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
import skimage
from scipy import ndimage
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import matplotlib as mpl
from myna.core.workflow.load_input import load_input
import argparse
import sys
import random


def cluster_colormap(n_digits, colorspace="tab20"):
    colors = mpl.cm.get_cmap(colorspace, n_digits)
    colorValues = np.linspace(0, 1, n_digits)
    colors = colors(colorValues)
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "custom_cmap", colors, N=n_digits
    )
    return [colors, cmap, colorValues]


def plot_image_with_no_labels(ax, image, cmap, title=""):
    """Plot all segments from the given image"""
    ax.imshow(image, origin="lower", cmap=cmap)
    ax.set_title(title)
    ax.xaxis.set_ticklabels([])
    ax.yaxis.set_ticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    return


def plot_rve_loc(ax, distances, pole, pole_x, pole_y, title=""):
    """Plot RVE location over the largest segment"""

    # Plot distances
    ax.imshow(distances, origin="lower", cmap="inferno")

    # Overlay RVE location
    ax.scatter(
        pole[1],
        pole[0],
        marker="x",
        s=8,
        color="red",
        label=f"X = {pole_x:.3f} mm,\nY = {pole_y:.3f} mm",
    )
    rect = Rectangle((pole[1] - 2, pole[0] - 2), 4, 4)
    pc = PatchCollection([rect], facecolor="none", alpha=1, edgecolor="red")
    ax.add_collection(pc)

    # Format axis
    ax.set_title(title)
    ax.xaxis.set_ticklabels([])
    ax.yaxis.set_ticklabels([])
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend()

    return


def run_rve_selection(
    settings, myna_file, myna_id_files, bid, max_layers_per_region=25
):
    # TODO (overall):
    # - Figure out how to handle multiple layers in the RVE selection
    # - Move away from the old settings format to the updated input file format

    # Create output directory if it doesn't already exist
    output_dir = os.path.join(os.path.dirname(myna_file), "output")
    os.makedirs(output_dir, exist_ok=True)

    # Initialize lists for region part and start/stop layers
    l0s = []
    l1s = []
    pns = []
    filesets = []
    last_part = None
    last_layer = None

    # Iterate through files and figure out if the layers are adjacent
    for myna_id_file in sorted(myna_id_files):
        print(f"Checking {myna_id_file}...")
        # Parse info from file path
        split_path = myna_id_file.split(os.path.sep)
        app = split_path[-2]
        layer = int(split_path[-3])
        part = split_path[-4]
        is_last_layer = myna_id_file == myna_id_files[-1]

        # Determine if part & layer are adjacent to last layer
        # and if not, then write region info to lists
        if last_part is not None:
            if (
                (part == last_part)
                and (layer == last_layer + 1)
                and (not is_last_layer)
            ):
                l1 = layer
                fileset.append(myna_id_file)
            elif (part == last_part) and (layer == last_layer + 1) and (is_last_layer):
                l0s.append(l0)
                l1s.append(layer)
                pns.append(part)
                fileset.append(myna_id_file)
                filesets.append(fileset)
            elif (l1 - l0) > max_layers_per_region:
                l0s.append(l0)
                l1s.append(l1 - 1)
                pns.append(last_part)
                filesets.append(fileset)
                l0 = layer
                l1 = layer
                fileset = [myna_id_file]
            else:
                l0s.append(l0)
                l1s.append(l1)
                pns.append(last_part)
                filesets.append(fileset)
                l0 = layer
                l1 = layer
                fileset = [myna_id_file]

        # Handle first file
        else:
            l0 = layer
            l1 = layer
            fileset = [myna_id_file]

        # Update "last" parameters
        last_part = part
        last_layer = layer

    # Initialize arrays for exporting data to the expected file
    pole_xs = []
    pole_ys = []
    ids = []
    layer_starts = []
    layer_ends = []
    ps = []
    region_dfs = []

    # Iterate through the groups
    # TODO: Update to handle multiple layers
    for fs, l0, l1, p in zip(filesets, l0s, l1s, pns):
        # For each file in the group
        region_df = None
        print(f"Part {p}, Layer(s) {l0} to {l1}:")
        for il, f in enumerate(fs):
            # Load and extract the top-surface data
            df = pd.read_csv(f)
            df["layer"] = l0 + il

            # Round to the nearest micron
            df = df.round(6)

            # Concatenate dataframes for the region
            if region_df is None:
                region_df = df.copy()
            else:
                region_df = pd.concat([region_df, df])

            # Create a meshgrid
            xs = sorted(df["x (m)"].unique())
            ys = sorted(df["y (m)"].unique())
            nx = len(xs)
            ny = len(ys)
            xx, yy = np.meshgrid(xs, ys, indexing="ij")

            # Print output
            print(f"\t{f}:")
            print(f"\t- x: ({np.min(xs)}, {np.max(xs)})")
            print(f"\t- y: ({np.min(ys)}, {np.max(ys)})")
            print(f"\t- nx, ny: {nx}, {ny}")

        # Shift layer grids to be coincident
        minx = region_df["x (m)"].min()
        miny = region_df["y (m)"].min()
        for l in region_df["layer"].unique():
            # Mask current layer
            mask = region_df["layer"] == l

            # Get grid spacing for the layer
            nx = len(region_df.loc[mask, "x (m)"].unique())
            ny = len(region_df.loc[mask, "y (m)"].unique())
            dx = np.round((np.max(xs) - np.min(xs)) / nx, 5)
            dy = np.round((np.max(ys) - np.min(ys)) / ny, 5)

            # Shift layer based on bounds compared to global bounds
            # such that the layer aligns with the global grid
            minx_layer = region_df.loc[mask, "x (m)"].min()
            miny_layer = region_df.loc[mask, "y (m)"].min()
            old_xs = sorted(region_df.loc[mask, "x (m)"].unique())
            old_ys = sorted(region_df.loc[mask, "y (m)"].unique())
            new_xs = (
                minx
                + np.arange(nx) * dx
                + dx * np.floor(np.abs(minx - minx_layer) / dx)
            )
            new_ys = (
                miny
                + np.arange(ny) * dy
                + dy * np.floor(np.abs(miny - miny_layer) / dy)
            )

            # Update values in region_df
            for old_x, new_x in zip(old_xs, new_xs):
                mask_x = (region_df["layer"] == l) & (region_df["x (m)"] == old_x)
                region_df.loc[mask_x, "x (m)"] = new_x
            for old_y, new_y in zip(old_ys, new_ys):
                mask_y = (region_df["layer"] == l) & (region_df["y (m)"] == old_y)
                region_df.loc[mask_y, "y (m)"] = new_y
            minx_layer = region_df.loc[mask, "x (m)"].min()
            miny_layer = region_df.loc[mask, "y (m)"].min()

        # Print number of unique x and y values in region_df
        region_df.round(6)
        print(f'nx (region) = {len(region_df["x (m)"].unique())}')
        print(f'ny (region) = {len(region_df["y (m)"].unique())}')

        # Get colormap for plotting
        n_digits = len(region_df["id"].unique())
        if n_digits <= 10:
            colorspace = "tab10"
        else:
            colorspace = "tab20"
        colors, cmap, colorValues = cluster_colormap(n_digits, colorspace=colorspace)

        # Aggregate region_df to a 2D image by taking the mode of the ids
        # for each (x,y) position. If multiple modes, than select one at random
        # using a fixed random seed
        random.seed(0)
        agg_ids = region_df.groupby(["x (m)", "y (m)"])["id"].agg(
            lambda x: random.choice(pd.Series.mode(x))
        )

        # Extract each cluster id from the dataset using the max area region
        # in a layer as the most representative
        zz = agg_ids.to_numpy().reshape(xx.shape)
        zz = zz.T
        for id in sorted(df["id"].unique()):
            # Skip background ID
            if id == bid:
                continue

            # Get labeled segments for the given cluster ID
            image = zz == id
            labeled_image, count = skimage.measure.label(
                image, connectivity=2, return_num=True
            )

            # Get table of values
            table = skimage.measure.regionprops_table(
                labeled_image, properties=("label", "area")
            )

            # Zero out labels not meeting condition, see:
            # - https://stackoverflow.com/questions/68540950/filter-regions-using-skimage-regionprops-and-create-a-mask-with-filtered-compone
            condition = table["area"] == np.max(table["area"])
            input_labels = table["label"]
            output_labels = input_labels * condition
            filtered_label_image = skimage.util.map_array(
                labeled_image, input_labels, output_labels
            )

            # Pad image
            filtered_label_image = np.pad(filtered_label_image, (1, 1))

            # Get max distance point
            distances = ndimage.distance_transform_edt(filtered_label_image)
            if np.max(distances) > 1:
                pole = np.unravel_index(
                    np.argmax(distances), distances.shape, order="C"
                )

                # Store data to output lists
                pole_x = xs[pole[1]]
                pole_y = ys[pole[0]]
                ids.append(id)
                layer_starts.append(l0)
                layer_ends.append(l1)
                ps.append(p)
                pole_xs.append(pole_x)
                pole_ys.append(pole_y)

                # Generate and save the summary figure
                fig, axs = plt.subplots(nrows=1, ncols=3, figsize=(9, 3))
                plot_image_with_no_labels(axs[0], zz, cmap=cmap, title="All Clusters")
                plot_image_with_no_labels(
                    axs[1],
                    labeled_image,
                    cmap="inferno",
                    title=f"Cluster {id} Segments",
                )
                plot_rve_loc(
                    axs[2],
                    distances,
                    pole,
                    pole_x,
                    pole_y,
                    title=f"Cluster {id} Largest Segment & RVE",
                )
                plt.savefig(
                    os.path.join(
                        output_dir,
                        os.path.basename(f).replace(".csv", f"_{id}_segment.png"),
                    ),
                    dpi=300,
                )
                plt.close()

            else:
                print(
                    f"{f}, cluster {id}: Insufficient cluster size for finding representative region"
                )

    export = pd.DataFrame(
        {
            "id": ids,
            "x (m)": pole_xs,
            "y (m)": pole_ys,
            "layer_starts": layer_starts,
            "layer_ends": layer_ends,
            "part": ps,
        }
    )
    export = export.astype(
        {
            "id": np.int64,
            "x (m)": np.float64,
            "y (m)": np.float64,
            "layer_starts": np.int64,
            "layer_ends": np.int64,
            "part": "string",
        }
    )

    export.to_csv(myna_file, index=False)

    return


def main(argv=None):
    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch RVE selection for specified input file"
    )

    parser.add_argument(
        "--bid",
        dest="bid",
        default=0,
        type=int,
        help="id for background region",
    )

    # Parse arguments
    args = parser.parse_args(argv)
    bid = args.bid

    # Get input settings
    input_file = os.environ["MYNA_INPUT"]
    settings = load_input(input_file)

    # Get expected Myna output files
    step_name = os.environ["MYNA_STEP_NAME"]
    myna_files = settings["data"]["output_paths"][step_name]

    # Get cluster ID files from previous step
    last_step_name = os.environ["MYNA_LAST_STEP_NAME"]
    myna_id_files = settings["data"]["output_paths"][last_step_name]

    # Get RVE selection
    for myna_file in myna_files:
        run_rve_selection(settings, myna_file, myna_id_files, bid)


if __name__ == "__main__":
    main(sys.argv[1:])
