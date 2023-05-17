import glob
import os
import pandas as pd
import numpy as np
import skimage
from scipy import ndimage
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection
from matplotlib.patches import Rectangle
import matplotlib as mpl

def cluster_colormap(n_digits, colorspace="tab20"):
    colors = mpl.cm.get_cmap(colorspace, n_digits)
    colorValues = np.linspace(0, 1, n_digits)
    colors = colors(colorValues)
    cmap = mpl.colors.LinearSegmentedColormap.from_list("custom_cmap", colors, N=n_digits)
    return [colors, cmap, colorValues]

def run_rve_selection(settings):
    n_digits = 4
    colors, cmap, colorValues = cluster_colormap(n_digits, colorspace="tab10")

    files = settings["classification"]["results"]
    l0s = []
    l1s = []
    part_numbers = []
    for part in settings["3DThesis"]["parts"]:
        part_numbers.append(part["part_number"])
        l0s.append(part["layer_start"])
        l1s.append(part["layer_end"])

    # Set up results directory
    if not os.path.exists(settings["rve"]["output_dir_path"]):
        os.makedirs(settings["rve"]["output_dir_path"])

    # Arrays for exporting data
    pole_xs = []
    pole_ys = []
    ids = []
    layer_starts = []
    layer_ends = []
    ps = []

    for f, l0, l1, p in zip(files, l0s, l1s, part_numbers): 

        df = pd.read_csv(f)
        xs = sorted(df["X(mm)"].unique())
        ys = sorted(df["Y(mm)"].unique())
        nx = len(xs)
        ny = len(ys)
        xx, yy = np.meshgrid(xs, ys, indexing='ij')

        print(f"Part {p}, Layer(s) {l0} to {l1}:")
        print(f"\t{np.min(xs)=}, {np.max(xs)=}")
        print(f"\t{np.min(ys)=}, {np.max(ys)=}")

        zz = df["id"].to_numpy().reshape(xx.shape)
        zz = zz.T
        unmelted_cluster_id = 1
        for id in sorted(df["id"].unique()):
            if id == unmelted_cluster_id:
                continue

            # Get labeled segments for the given cluster ID
            image = zz == id
            labeled_image, count = skimage.measure.label(image, connectivity=2, return_num=True)

            # Get table of values
            table = skimage.measure.regionprops_table(labeled_image, properties=("label", "area"))

            # Zero out labels not meeting condition
            # https://stackoverflow.com/questions/68540950/filter-regions-using-skimage-regionprops-and-create-a-mask-with-filtered-compone
            condition = (table["area"] == np.max(table["area"]))
            input_labels = table["label"]
            output_labels = input_labels * condition
            filtered_label_image = skimage.util.map_array(labeled_image, input_labels, output_labels)

            # Pad image
            filtered_label_image = np.pad(filtered_label_image, (1,1))

            # Get max distance point
            distances = ndimage.distance_transform_edt(filtered_label_image)
            if np.max(distances) > 1:
                pole = (np.unravel_index(np.argmax(distances), distances.shape))

                fig, axs = plt.subplots(nrows=1, ncols=3, figsize=(9, 3))

                axs[0].imshow(zz, origin="lower", cmap=cmap)
                axs[0].set_title("All Clusters")
                axs[0].xaxis.set_ticklabels([])
                axs[0].yaxis.set_ticklabels([])
                axs[0].set_xticks([])
                axs[0].set_yticks([])

                axs[1].imshow(labeled_image, origin="lower", cmap="inferno")
                axs[1].set_title(f"Cluster {id} Segments")
                axs[1].xaxis.set_ticklabels([])
                axs[1].yaxis.set_ticklabels([])
                axs[1].set_xticks([])
                axs[1].set_yticks([])

                # Plot RVE location over the largest segment
                ids.append(id)
                layer_starts.append(l0)
                layer_ends.append(l1)
                pole_x = xs[pole[0]]
                pole_y = ys[pole[1]]
                ps.append(p)
                pole_xs.append(1e-3*pole_x)
                pole_ys.append(1e-3*pole_y)
                axs[2].imshow(filtered_label_image, origin="lower", cmap="binary_r")
                axs[2].scatter(pole_x, pole_y, marker = "x", s=8, color="red", label=f"X = {pole_x:.3f} mm,\nY = {pole_y:.3f} mm")
                rect = Rectangle((pole[1] - 2, pole[0] - 2), 4, 4)
                pc = PatchCollection([rect], facecolor="none", alpha=1, edgecolor="red")
                axs[2].add_collection(pc)
                axs[2].set_title(f"Cluster {id} Largest Segment & RVE")
                axs[2].xaxis.set_ticklabels([])
                axs[2].yaxis.set_ticklabels([])
                axs[2].set_xticks([])
                axs[2].set_yticks([])
                axs[2].legend()
                plt.savefig(
                    os.path.join(settings["rve"]["output_dir_path"],
                                 os.path.basename(f).replace(".csv", f"_{id}_segment.png")), 
                    dpi=300)
                plt.close()

            else:
                print(f"{f}, cluster {id}: Insufficient cluster size for finding representative region")

    export = pd.DataFrame({"id":ids, 
                           "x (m)":pole_xs, 
                           "y (m)":pole_ys, 
                           "layer_starts":layer_starts, 
                           "layer_ends":layer_ends, 
                           "part_number":ps})
    result_path = os.path.join(settings["rve"]["output_dir_path"],"rve_list.csv")
    export.to_csv(result_path, index=False)
    
    return result_path