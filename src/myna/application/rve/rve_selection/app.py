#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for rve/rve_selection."""

import os
import random
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import skimage
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
from scipy import ndimage
from myna.core.workflow import config, write_input
from myna.application.rve import RVE


class RVESelection(RVE):
    """Select representative RVE locations based on segmented ID maps."""

    def __init__(self):
        super().__init__()
        self.class_name = "rve_selection"

    def parse_execute_arguments(self):
        self.parse_shared_arguments()
        self.register_argument(
            "--bid",
            dest="bid",
            default=0,
            type=int,
            help="id for background region",
        )
        self.register_argument(
            "--max-layers-per-region",
            default=25,
            type=int,
            help="(int) max adjacent layers to keep in each grouped region",
        )
        self.parse_known_args()

    def parse_postprocess_arguments(self):
        self.parse_shared_arguments()
        self.parse_known_args()

    @staticmethod
    def cluster_colormap(n_digits, colorspace="tab20"):
        colors = mpl.cm.get_cmap(colorspace, n_digits)
        color_values = np.linspace(0, 1, n_digits)
        colors = colors(color_values)
        cmap = mpl.colors.LinearSegmentedColormap.from_list(
            "custom_cmap", colors, N=n_digits
        )
        return [colors, cmap, color_values]

    @staticmethod
    def plot_image_with_no_labels(ax, image, cmap, title=""):
        """Plot all segments from the given image."""
        ax.imshow(image, origin="lower", cmap=cmap)
        ax.set_title(title)
        ax.xaxis.set_ticklabels([])
        ax.yaxis.set_ticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])

    @staticmethod
    def plot_rve_loc(ax, distances, pole, pole_x, pole_y, title=""):
        """Plot RVE location over the largest segment."""
        ax.imshow(distances, origin="lower", cmap="inferno")
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
        ax.set_title(title)
        ax.xaxis.set_ticklabels([])
        ax.yaxis.set_ticklabels([])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.legend()

    def run_rve_selection(self, myna_file, myna_id_files, bid, max_layers_per_region):
        """Run RVE selection for one output file."""
        output_dir = os.path.join(os.path.dirname(myna_file), "output")
        os.makedirs(output_dir, exist_ok=True)

        l0s = []
        l1s = []
        pns = []
        fileset = []
        filesets = []
        l0 = None
        last_part = None
        last_layer = None

        for myna_id_file in sorted(myna_id_files):
            print(f"Checking {myna_id_file}...")
            split_path = myna_id_file.split(os.path.sep)
            layer = int(split_path[-3])
            part = split_path[-4]
            is_last_layer = myna_id_file == myna_id_files[-1]

            if last_part is not None:
                if (
                    (part == last_part)
                    and (layer == last_layer + 1)
                    and (not is_last_layer)
                ):
                    l1 = layer
                    fileset.append(myna_id_file)
                elif (
                    (part == last_part) and (layer == last_layer + 1) and is_last_layer
                ):
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
            else:
                l0 = layer
                l1 = layer
                fileset = [myna_id_file]

            last_part = part
            last_layer = layer

        pole_xs = []
        pole_ys = []
        ids = []
        layer_starts = []
        layer_ends = []
        ps = []

        for fs, l0, l1, p in zip(filesets, l0s, l1s, pns):
            region_df = None
            print(f"Part {p}, Layer(s) {l0} to {l1}:")
            for il, filename in enumerate(fs):
                df = pd.read_csv(filename)
                df["layer"] = l0 + il
                df = df.round(6)

                if region_df is None:
                    region_df = df.copy()
                else:
                    region_df = pd.concat([region_df, df])

                xs = sorted(df["x (m)"].unique())
                ys = sorted(df["y (m)"].unique())
                nx = len(xs)
                ny = len(ys)
                xx, yy = np.meshgrid(xs, ys, indexing="ij")
                print(f"\t{filename}:")
                print(f"\t- x: ({np.min(xs)}, {np.max(xs)})")
                print(f"\t- y: ({np.min(ys)}, {np.max(ys)})")
                print(f"\t- nx, ny: {nx}, {ny}")

            minx = region_df["x (m)"].min()
            miny = region_df["y (m)"].min()
            for layer in region_df["layer"].unique():
                mask = region_df["layer"] == layer

                nx = len(region_df.loc[mask, "x (m)"].unique())
                ny = len(region_df.loc[mask, "y (m)"].unique())
                dx = np.round((np.max(xs) - np.min(xs)) / nx, 5)
                dy = np.round((np.max(ys) - np.min(ys)) / ny, 5)

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

                for old_x, new_x in zip(old_xs, new_xs):
                    mask_x = (region_df["layer"] == layer) & (
                        region_df["x (m)"] == old_x
                    )
                    region_df.loc[mask_x, "x (m)"] = new_x
                for old_y, new_y in zip(old_ys, new_ys):
                    mask_y = (region_df["layer"] == layer) & (
                        region_df["y (m)"] == old_y
                    )
                    region_df.loc[mask_y, "y (m)"] = new_y

            region_df.round(6)
            print(f"nx (region) = {len(region_df['x (m)'].unique())}")
            print(f"ny (region) = {len(region_df['y (m)'].unique())}")

            n_digits = len(region_df["id"].unique())
            colorspace = "tab10" if n_digits <= 10 else "tab20"
            colors, cmap, color_values = self.cluster_colormap(
                n_digits, colorspace=colorspace
            )

            random.seed(0)
            agg_ids = region_df.groupby(["x (m)", "y (m)"])["id"].agg(
                lambda x: random.choice(pd.Series.mode(x))
            )

            zz = agg_ids.to_numpy().reshape(xx.shape)
            zz = zz.T
            for cluster_id in sorted(df["id"].unique()):
                if cluster_id == bid:
                    continue

                image = zz == cluster_id
                labeled_image, count = skimage.measure.label(
                    image, connectivity=2, return_num=True
                )

                table = skimage.measure.regionprops_table(
                    labeled_image, properties=("label", "area")
                )
                condition = table["area"] == np.max(table["area"])
                input_labels = table["label"]
                output_labels = input_labels * condition
                filtered_label_image = skimage.util.map_array(
                    labeled_image, input_labels, output_labels
                )

                filtered_label_image = np.pad(filtered_label_image, (1, 1))

                distances = ndimage.distance_transform_edt(filtered_label_image)
                if np.max(distances) > 1:
                    pole = np.unravel_index(
                        np.argmax(distances), distances.shape, order="C"
                    )

                    pole_x = xs[pole[1]]
                    pole_y = ys[pole[0]]
                    ids.append(cluster_id)
                    layer_starts.append(l0)
                    layer_ends.append(l1)
                    ps.append(p)
                    pole_xs.append(pole_x)
                    pole_ys.append(pole_y)

                    fig, axs = plt.subplots(nrows=1, ncols=3, figsize=(9, 3))
                    self.plot_image_with_no_labels(
                        axs[0], zz, cmap=cmap, title="All Clusters"
                    )
                    self.plot_image_with_no_labels(
                        axs[1],
                        labeled_image,
                        cmap="inferno",
                        title=f"Cluster {cluster_id} Segments",
                    )
                    self.plot_rve_loc(
                        axs[2],
                        distances,
                        pole,
                        pole_x,
                        pole_y,
                        title=f"Cluster {cluster_id} Largest Segment & RVE",
                    )
                    plt.savefig(
                        os.path.join(
                            output_dir,
                            os.path.basename(filename).replace(
                                ".csv", f"_{cluster_id}_segment.png"
                            ),
                        ),
                        dpi=300,
                    )
                    plt.close()
                else:
                    print(
                        f"{filename}, cluster {cluster_id}: Insufficient cluster size "
                        "for finding representative region"
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

    def execute(self):
        """Execute the RVE selection algorithm for all expected outputs."""
        self.parse_execute_arguments()
        myna_files = self.settings["data"]["output_paths"][self.step_name]
        myna_id_files = self.settings["data"]["output_paths"][self.last_step_name]
        for myna_file in myna_files:
            self.run_rve_selection(
                myna_file,
                myna_id_files,
                self.args.bid,
                self.args.max_layers_per_region,
            )

    def postprocess(self):
        """Populate region metadata from generated RVE selection files."""
        self.parse_postprocess_arguments()
        myna_files = self.settings["data"]["output_paths"][self.step_name]

        for part in self.settings["data"]["build"]["parts"]:
            values = self.settings["data"]["build"]["parts"][part].get("regions")
            if values is None:
                self.settings["data"]["build"]["parts"][part]["regions"] = {}

        for myna_file in myna_files:
            df = pd.read_csv(
                myna_file,
                dtype={
                    "id": np.int64,
                    "x (m)": np.float64,
                    "y (m)": np.float64,
                    "layer_starts": np.int64,
                    "layer_ends": np.int64,
                    "part": "string",
                },
            )
            for row in df.to_dict(orient="records"):
                part = str(row["part"])
                region = f"rve_{row['id']}"
                layer_start = int(row["layer_starts"])
                layer_end = int(row["layer_ends"])
                self.settings["data"]["build"]["parts"][part]["regions"][region] = {
                    "x": row["x (m)"],
                    "y": row["y (m)"],
                    "layer_starts": layer_start,
                    "layer_ends": layer_end,
                    "layers": [x for x in range(layer_start, layer_end + 1)],
                }

        write_input(self.settings, self.input_file)
        config.config(self.input_file)
