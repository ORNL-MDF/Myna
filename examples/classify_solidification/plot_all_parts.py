import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import glob
import os
import numpy as np

# Get part directories
part_dirs = sorted(glob.glob(os.path.join(".", "demo_build", "P*")))

# Extract files
files = []
for part_dir in part_dirs:
    file_list = sorted(
        glob.glob(
            os.path.join(
                part_dir,
                "*",
                "classification_supervoxel_relabel",
                "class_supervoxels",
                "class_supervoxel*.png",
            )
        )
    )
    files.extend(file_list)

# Get part numbers from file names
part_nums = [int(f.split(os.path.sep)[2].replace("P", "")) for f in files]
layer_nums = [int(f.split(os.path.sep)[3]) for f in files]

# Set up the plot
nrows = 1
ncols = 4
fig, axs = plt.subplots(nrows=nrows, ncols=ncols, figsize=(ncols * 3, nrows * 4))
plt.rcParams["axes.titlepad"] = -12  # pad is in points...

# Load images into the plot
print("Loading image files")
for index, (f, p, l) in enumerate(zip(files, part_nums, layer_nums)):
    img = mpimg.imread(f)
    if (ncols == 1) or (nrows == 1):
        ax = axs[index]
    else:
        i = index % (ncols)
        j = nrows - int(np.floor(index / ncols)) - 1
        ax = axs[j, i]
    ax.imshow(img)
    ax.set_aspect(1)
    ax.axis("off")
    ax.set_title(f"P{p} Layer {l}", fontsize=8)

# Exporting merged images
print("Writing combined image")
plt.tight_layout(h_pad=0, w_pad=0)
plt.savefig("all_supervoxel_maps.png", dpi=300)
plt.close()
