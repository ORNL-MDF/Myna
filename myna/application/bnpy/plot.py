""" Functions for generating plots of clustering data
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import matplotlib as mpl
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.ticker as mticker
import copy


def emptyTicks(x, pos):
    """
    Return blank ticks for matplotlib.ticker.FuncFormatter()
    """
    label = ""
    return label


def cluster_colormap(n_digits, colorspace="tab20"):
    """
    Return colormap RGB colors, matplotlib colormap object, and color floats
    """
    colors = mpl.cm.get_cmap(colorspace, n_digits)
    colorValues = np.linspace(0, 1, n_digits)
    colors = colors(colorValues)
    cmap = mpl.colors.LinearSegmentedColormap.from_list(
        "custom_cmap", colors, N=n_digits
    )
    return [colors, cmap, colorValues]


def pd_normalized_histogram(dataframe, scaledRanges, xmin=0, xmax=1, dpi=150):
    """
    Plot distribution of values for each column in a pandas.dataFrame
    """
    for i, col in enumerate(dataframe.columns):
        print(f"Generating normalized histogram for distribution of {col}")
        minVal = scaledRanges["Min Value"][i]
        maxVal = scaledRanges["Max Value"][i]
        n, x, _ = plt.hist(
            (dataframe[col] - xmin) / (xmax - xmin),
            bins=101,
            range=[xmin, xmax],
            alpha=0.6,
            edgecolor="black",
        )
        plt.xlabel(f"{col} normalized value")
        plt.ylabel("Count")
        plt.title(f"Value range: ({minVal:.4g}, {maxVal:.4g})")
        plt.savefig(
            os.path.join("training_voxels", f"Training_Data_NormHist.{col}.png"),
            dpi=dpi,
        )
        plt.close()
    return


def pd_histogram(dataframe, scaledRanges, dpi=150):
    """
    Plot distribution of values for each column in a pandas dataframe
    """
    for i, col in enumerate(dataframe.columns):
        print(f"Generating histogram for distribution of {col}")
        minVal = scaledRanges["Min Value"][i]
        maxVal = scaledRanges["Max Value"][i]
        n, x, _ = plt.hist(
            minVal + dataframe[col] * (maxVal - minVal),
            bins=101,
            alpha=0.6,
            edgecolor="black",
        )
        plt.xlabel(f"{col}")
        plt.ylabel("Count")
        plt.savefig(
            os.path.join("training_voxels", f"Training_Data_Hist.{col}.png"), dpi=dpi
        )
        plt.close()
    return


def voxel_GV_plot(df, colors, cmap, exportName, dpi=150):
    """
    Plot GV plot for a cluster pandas.dataFrame with the given colormap
    """
    fig = plt.figure(figsize=(9, 4))
    ax = plt.gca()

    for i in df["id"].unique():
        plotdata = df[df["id"] == i]
        plotdata = plotdata.sample(min(1000, len(plotdata)), axis=0, random_state=42)
        ax.scatter(
            np.power(10, plotdata["logV"]),
            np.power(10, plotdata["logG"]),
            color=colors[i],
            alpha=0.5,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")

    ax.set_aspect("auto")
    ax.set_xlabel("V")
    ax.set_ylabel("G")

    # Create the colorbar
    divider1 = make_axes_locatable(ax)
    cax1 = divider1.append_axes("right", size="5%", pad=0.05)
    mappable1 = ax.collections[0]
    cbar1 = fig.colorbar(mappable=mappable1, cax=cax1)

    # Draw colorbar for cluster IDs
    bounds = np.arange(len(colors) + 1)
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
    cbar = mpl.colorbar.ColorbarBase(
        cax1,
        cmap=cmap,
        norm=norm,
        boundaries=bounds,
        ticks=bounds + 0.5,
        spacing="proportional",
        orientation="vertical",
        label="Cluster ID",
    )

    cbarTicks = cbar.get_ticks()
    cbarLabels = [
        f"{x:.2g}"
        for x in np.linspace(np.min(df["id"]), np.max(df["id"]), len(cbarTicks))
    ]
    cbar.locator = mpl.ticker.FixedLocator(cbarTicks)
    cbar.formatter = mpl.ticker.FixedFormatter(cbarLabels)
    cbar.update_ticks()
    plt.tight_layout()
    plt.savefig(os.path.join("cluster_voxels", exportName), dpi=dpi)
    plt.close()
    return


def voxel_id_stacked_histogram(
    df, field, colors, exportName, dpi=150, ids=None, verbose=False
):
    """
    Plot stacked histogram for clustering training data
    """
    if ids is None:
        labelList = np.unique(df["id"])
    else:
        labelList = ids
    if verbose:
        print(f"Generating voxel class stacked histogram for {field}")
    plt.figure(1)
    xmin, xmax = [df[field].min(), df[field].max()]
    labels = []
    hists = []
    for i in labelList:
        hists.append((df[df["id"] == i][field] - xmin) / (xmax - xmin))
        labels.append(f"{i}")
    n, x, _ = plt.hist(
        hists,
        bins=101,
        range=[0, 1],
        color=colors,
        label=labels,
        alpha=1.0,
        histtype="barstacked",
        stacked=True,
    )
    ax = plt.gca()
    box = ax.get_position()
    ax.set_position(
        [box.x0, box.y0, box.width * 0.8, box.height]
    )  # Shrink current axis by 20%
    ax.legend(
        ncol=2, loc="center left", bbox_to_anchor=(1, 0.5), title="Cluster ID"
    )  # Put a legend to the right of the current axis
    plt.xlabel(f"{field} (normalized)")
    plt.ylabel("Count")
    plt.title(f"x range: ({xmin:.4g}, {xmax:.4g})")
    plt.savefig(os.path.join("cluster_voxels", exportName), dpi=dpi)
    plt.close()
    return


def cluster_composition_map(xx, yy, mesh, cluster, exportName, dpi=150):
    """
    Plot the spatial map of supervoxel composition for a specific cluster given a supervoxel mesh
    """
    plt.pcolormesh(
        xx,
        yy,
        np.reshape(mesh[f"comp_{cluster}"].to_numpy(), xx.shape),
        edgecolor="black",
        cmap="viridis",
        shading="nearest",
    )
    plt.colorbar(label=f"cluster {cluster} fraction")
    ax = plt.gca()
    ax.set_aspect(1.0)
    plt.xlabel("X (mm)")
    plt.ylabel("Y (mm)")
    plt.savefig(os.path.join("cluster_supervoxels", exportName), dpi=dpi)
    plt.close()
    return


def supervoxel_composition_hist(meshData, col, exportName, xmin=0, xmax=1, dpi=150):
    """
    Plot a histogram of the volume fraction of composition for each cluster given a supervoxel mesh
    """
    n, x, _ = plt.hist(
        (meshData[col] - xmin) / (xmax - xmin),
        bins=101,
        range=[xmin, xmax],
        alpha=0.6,
        edgecolor="black",
    )
    plt.xlabel(f"{col} normalized value")
    plt.ylabel("Count")
    plt.title(f"Value range: ({meshData[col].min():.4g}, {meshData[col].max():.4g})")
    plt.savefig(os.path.join("cluster_supervoxels", exportName), dpi=dpi)
    plt.close()
    return


def supervoxel_id_colormesh(
    mesh, colorValues, cmap, exportName, writeDir="cluster_supervoxels", dpi=150
):
    """
    Plot a colormesh of the supervoxel clustering IDs given a cluster supervoxel mesh and colormap
    """
    fig, axs = plt.subplots(nrows=1, ncols=1, figsize=(5, 4), dpi=dpi)
    nx = len(mesh["X(mm)"].round(3).unique())
    ny = len(mesh["Y(mm)"].round(3).unique())
    xx = mesh["X(mm)"].to_numpy().reshape((nx, ny))
    yy = mesh["Y(mm)"].to_numpy().reshape((nx, ny))
    n_digits = len(colorValues)
    dataColors = [colorValues[i] for i in mesh["id"]]
    dataColors = np.reshape(dataColors, xx.shape)
    axs.pcolormesh(
        xx,
        yy,
        dataColors,
        cmap=cmap,
        linewidth=0.1,
        edgecolors="black",
        shading="nearest",
    )
    axs.set_aspect(1)
    axs.set_xlabel("X (mm)")
    axs.set_ylabel("Y (mm)")

    # Draw colorbar
    divider1 = make_axes_locatable(axs)
    cax1 = divider1.append_axes("right", size="5%", pad=0.05)
    mappable = axs.collections[0]
    bounds = np.arange(n_digits + 1)
    norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
    cbar = mpl.colorbar.ColorbarBase(
        cax1,
        cmap=cmap,
        norm=norm,
        boundaries=bounds,
        ticks=bounds + 0.5,
        spacing="proportional",
        orientation="vertical",
        label="Cluster ID",
    )

    cbarTicks = cbar.get_ticks()
    cbarLabels = [f"{x:.2g}" for x in np.linspace(0, n_digits, len(cbarTicks))]
    cbar.locator = mpl.ticker.FixedLocator(cbarTicks)
    cbar.formatter = mpl.ticker.FixedFormatter(cbarLabels)
    cbar.update_ticks()
    plt.tight_layout()
    plt.savefig(os.path.join(writeDir, exportName), dpi=dpi)
    plt.close()
    return


def combined_composition_colormesh(id, nrows=3, ncols=5, dpi=150):
    """
    For all datasets in "training_supervoxels", plot spatial composition maps for each cluster in
    a single plot.
    """
    # Add a new field to track fraction of points in each mesh grid for each cluster
    meshCompCSV = os.path.join(
        "training_supervoxels", f"Dataset_{id}.Supervoxel_Composition.csv"
    )

    if not os.path.exists(meshCompCSV):
        print(f"Cannot find composition data for dataset {id}")
        return
    else:
        mesh = pd.read_csv(meshCompCSV)

    clusters = []
    for col in mesh.columns:
        if col[:5] == "comp_":
            clusters.append(col[5:])

    fig, axs = plt.subplots(nrows=nrows, ncols=ncols, sharex="col", sharey="row")

    # Set up numpy meshgrid
    nx = len(mesh["X(mm)"].unique())
    ny = len(mesh["Y(mm)"].unique())
    xx = mesh["X(mm)"].to_numpy().reshape((nx, ny))
    yy = mesh["Y(mm)"].to_numpy().reshape((nx, ny))

    minVal = 0
    maxVal = -1e6
    minValLog = 1e6
    maxValLog = -1e6
    for i, cluster in enumerate(clusters):
        maxVal = max(mesh[f"comp_{cluster}"].max(), maxVal)
        with np.errstate(divide="ignore"):
            mx = np.log10(mesh[f"comp_{cluster}"].max())
            mn = np.log10(mesh[mesh[f"comp_{cluster}"] > 0][f"comp_{cluster}"].min())
            if not np.isinf(mx):
                maxValLog = max(mx, maxValLog)
            if not np.isinf(mn):
                minValLog = min(mn, minValLog)

    singleColorScale = True
    showLabels = False
    for i, cluster in enumerate(clusters):
        col = i % ncols
        row = int(i / ncols)
        zz = np.reshape(mesh[f"comp_{cluster}"].to_numpy(), xx.shape)
        cmap = copy.copy(mpl.cm.get_cmap("viridis"))
        cmin = -4.0
        cmax = -0.1
        cmap.set_bad("black", 1.0)
        if singleColorScale:
            axs[row, col].pcolormesh(
                xx,
                yy,
                np.log10(zz),
                edgecolor="none",
                cmap=cmap,
                shading="nearest",
                vmin=cmin,
                vmax=cmax,
            )
        else:
            axs[row, col].pcolormesh(
                xx, yy, zz, edgecolor="none", cmap=cmap, shading="nearest"
            )
        if showLabels:
            if row == int(nrows / 2) and col == 0:
                axs[row, col].set_ylabel("Y (mm)")
            elif col == 0:
                axs[row, col].yaxis.set_major_formatter(
                    mticker.FuncFormatter(emptyTicks)
                )
            if col == int(ncols / 2) and row == nrows - 1:
                axs[row, col].set_xlabel("X (mm)")
            elif row == nrows - 1:
                axs[row, col].xaxis.set_major_formatter(
                    mticker.FuncFormatter(emptyTicks)
                )
        else:
            axs[row, col].xaxis.set_major_formatter(mticker.FuncFormatter(emptyTicks))
            axs[row, col].yaxis.set_major_formatter(mticker.FuncFormatter(emptyTicks))
        axs[row, col].set_aspect("equal")
        if i == 0:
            xlims = axs[row, col].get_xlim()
        else:
            axs[row, col].set_xlim(xlims)
        axs[row, col].text(
            0,
            1,
            f"{cluster}",
            fontsize=6,
            c="white",
            transform=axs[row, col].transAxes,
            ha="left",
            va="top",
        )

    if ncols * nrows > len(clusters):
        for i in range(len(clusters), ncols * nrows):
            col = i % (ncols)
            row = int(i / ncols)
            axs[row, col].pcolormesh(
                xx, yy, zz, edgecolor="none", cmap=cmap, shading="nearest"
            )
            axs[row, col].set_visible(False)

    plt.savefig(
        os.path.join(
            "training_supervoxels", f"Supervoxel.Dataset_{id}.Composition.png"
        ),
        dpi=dpi,
    )
    plt.close()

    # Plot colorbar for figures
    fig, ax = plt.subplots(figsize=(6, 1))
    fig.subplots_adjust(bottom=0.75)
    norm = mpl.colors.Normalize(vmin=cmin, vmax=cmax)
    fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=ax,
        orientation="horizontal",
        label="$log_{10}(V_i)$",
    )
    plt.savefig(
        os.path.join(
            "training_supervoxels", f"Supervoxel.Dataset_{id}.Composition.Colorbar.png"
        ),
        dpi=dpi,
    )
    plt.close()
