#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import vtk
from vtk.util.numpy_support import numpy_to_vtk
from .color import add_pyebsd_rgb_color
from .id import convert_id_to_rotation
from .vtk import grain_id_reader
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter


def add_rgb_to_vtk(
    vtk_file_path,
    vtk_export_path,
    lookup_name,
    dirs={"X": [1, 0, 0], "Y": [0, 1, 0], "Z": [0, 0, 1]},
):
    """Add RGB coloring to VTK file

    Args:
        vtk_file_path: path to VTK file to add RGB colors to
        vtk_export_path: path for export of modified VTK file
        lookup_name: path to the lookup table of Reference ID orientations (e.g., GrainOrientationVectors.csv)
    """

    # Read the VTK file
    reader = grain_id_reader(vtk_file_path)
    structured_points = reader.GetOutput()
    dims = structured_points.GetDimensions()
    origin = structured_points.GetOrigin()
    spacing = structured_points.GetSpacing()

    # Convert grain ids into Euler angles
    df = convert_id_to_rotation(reader, lookup_name)

    # Add colors to the DataFrame
    df = df.sort_values(by=["Z (m)", "Y (m)", "X (m)"])
    suffices = dirs.keys()
    directions = [dirs[key] for key in suffices]
    for suffix, dir in zip(suffices, directions):
        df = add_pyebsd_rgb_color(df, refDir=dir, suffix=suffix)

    # Initialize VTK structured points dataset
    vtk_dataset = vtk.vtkStructuredPoints()
    vtk_dataset.SetDimensions(dims)
    vtk_dataset.SetSpacing(spacing)
    vtk_dataset.SetOrigin(origin)

    # Add scalar data to vtk_dataset from dataframe
    scalar_names = ["Grain ID", "Reference ID"]
    scalar_types = [vtk.VTK_INT, vtk.VTK_INT]
    for col, val_type in zip(scalar_names, scalar_types):
        vtk_data = numpy_to_vtk(num_array=df[col].to_numpy(), array_type=val_type)
        vtk_data.SetName(col)
        vtk_dataset.GetPointData().AddArray(vtk_data)

    # Add vector data to vtk_dataset from df:
    # <"RX", "GX", "BX">, <"RY", "GY", "BY">, <"RZ", "GZ", "BZ">
    for suffix in suffices:
        cols = [f"R{suffix}", f"G{suffix}", f"B{suffix}"]
        # Add data as vector to VTK dataset
        vtk_data = numpy_to_vtk(
            num_array=df[cols].to_numpy(), deep=True, array_type=vtk.VTK_FLOAT
        )
        vtk_data.SetName(f"rgb{suffix}")
        vtk_dataset.GetPointData().AddArray(vtk_data)

    # Write file using VTK file writer
    writer = vtk.vtkDataSetWriter()
    writer.SetFileName(vtk_export_path)
    writer.SetInputData(vtk_dataset)
    writer.SetFileTypeToBinary()
    writer.Write()

    return


def extract_subregion(
    vtk_file_path, vtk_export_path, bounds=np.array([[0, 1], [0, 1], [0, 1]])
):
    """Extract a subvolume from the given VTK file

    Args:
        vtk_file_path: path to VTK file to to extract region from
        vtk_export_path: path for export of modified VTK file
        bounds: array of X, Y, and Z min & max bounds in terms of fraction of the overall volume dimensions
    """

    # Read the VTK file
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(vtk_file_path)
    reader.ReadAllScalarsOn()
    reader.Update()
    structured_points = reader.GetOutput()

    # Get the dimensions of the data
    dims = structured_points.GetDimensions()

    # Set the volume of interest
    x0 = np.clip(int(bounds[0][0] * dims[0]), 0, dims[0] - 1)
    x1 = np.clip(int(bounds[0][1] * dims[0]), 0, dims[0] - 1)
    y0 = np.clip(int(bounds[1][0] * dims[1]), 0, dims[1] - 1)
    y1 = np.clip(int(bounds[1][1] * dims[1]), 0, dims[1] - 1)
    z0 = np.clip(int(bounds[2][0] * dims[2]), 0, dims[2] - 1)
    z1 = np.clip(int(bounds[2][1] * dims[2]), 0, dims[2] - 1)

    # Extract the subvolume
    extractor = vtk.vtkExtractVOI()
    extractor.SetInputData(structured_points)
    extractor.SetVOI(x0, x1, y0, y1, z0, z1)
    extractor.Update()
    subvolume = extractor.GetOutput()

    # Write file using VTK file writer
    writer = vtk.vtkDataSetWriter()
    writer.SetFileName(vtk_export_path)
    writer.SetInputData(subvolume)
    writer.SetFileTypeToBinary()
    writer.Write()

    return


def plot_euler_angles(df, im_height, im_width, export_file="euler_angle_plots.png"):
    """Plot the three Euler angles (Bunge notation: phi1, Phi, phi2) from a pandas
    DataFrame

    Args:
      df: pandas DataFrame containing, at least, columns "phi1", "Phi", and "phi2"
      im_height: height of the data image in pixels
      im_width: width of the data image in pixels
      export_file: path to the exported plot
    """
    # Calculate and plot euler angles
    fig, axs = plt.subplots(nrows=1, ncols=3)
    for i, euler_angle in enumerate(["phi1", "Phi", "phi2"]):
        data = df[euler_angle].to_numpy().reshape(im_height, im_width)
        axs[i].imshow(data)
        axs[i].set_title(euler_angle)
        axs[i].axis("off")
    plt.tight_layout()
    plt.savefig(export_file)
    plt.close()
    return


def plot_poles(M, direction, ax=None):
    """Plot the pole figure for all N rotation matrices and return the pole data in Cartesian coordinates

    Args:
      M: array-like (N,3,3,) of rotation matrices for sample -> crystal coordinates (passive reference frame)
      direction: array-like (3,) describing the normal for the spherical projection
      ax: (default None) axis to use for plotting, if none, will create a new figure
        with a single axis.

    Returns:
      pole_data: numpy array of XY locations of the calculate poles such that
        `X=pole_data[:,0]` and `Y=pole_data[:,0]`.
    """

    try:
        from pyebsd.ebsd import plot_PF
    except ImportError as exc:
        raise ImportError(
            'Myna exaca app requires "pip install .[exaca]" optional dependencies!'
        ) from exc

    if ax is None:
        _, ax = plt.subplots()

    plot_PF(
        M=M,
        proj=direction,
        ax=ax,
        sel=None,
        rotation=None,
        contour=False,
        verbose=True,
        color="k",
    )
    circle = plt.Circle((0.0, 0.0), 1.0, fc="none", ec="k")
    ax.add_patch(circle)
    ax.set_title(f"{tuple(direction)}")
    ax.set_aspect(1)
    ax.axis("off")
    return ax


def plot_pole_density(
    M,
    direction,
    bins=None,
    use_multiples_of_random=True,
    levels=5,
    smooth_sigma=None,
    annotate_xy=True,
    ax=None,
):
    """Calculates and plots the pole density histogram in Cartesian coordinates on the
    specified axis

    Args:
      M: array-like (N,3,3,) of rotation matrices for sample -> crystal coordinates (passive reference frame)
      direction: array-like (3,) describing the normal for the spherical projection
      bins: (default None) integer number of bins to use for density calculation. If
        None, then calculate the number of bins as `int(sqrt(N))`.
      use_multiples_of_random: (default True) if True, will divide the histogram counts
        by the expected counts for a uniform/random distribution across the projection
        to plot the "multiples of random distribution" instead of histogram counts
      levels: (default 5) int of number of contour levels or array-like (N,) of specific
        levels to use in the contour plot. If an integer, levels will be chosen
        automatically based on data bounds.
      smooth_sigma: (default None) scalar or sequence of scalars input to the
        scipy.ndimage.gaussian_filter() sigma parameter for smooth the data along
        axes uniformly (scalar) or along each specified axis (sequence of scalars).
      ax: (default None) axis to use for plotting, if none, will create a new figure
        with a single axis.

    Returns:
      ax: axis with the pole figure
    """
    try:
        from pyebsd.ebsd import plot_PF
    except ImportError as exc:
        raise ImportError(
            'Myna exaca app requires "pip install .[exaca]" optional dependencies!'
        ) from exc

    # Get pole locations
    fig_temp, ax_temp = plt.subplots()
    ax_temp = plot_PF(
        M=M,
        proj=direction,
        ax=ax_temp,
        sel=None,
        rotation=None,
        contour=False,
        verbose=True,
    )
    pole_data = np.array(ax_temp.lines[0].get_xydata())
    plt.close(fig_temp)

    # Calculate histogram and get mesh centroids
    if bins is None:
        bins = int(np.sqrt(M.shape[0]))
    hist, xedges, yedges = np.histogram2d(
        pole_data[:, 1], pole_data[:, 0], bins=bins, range=[[-1, 1], [-1, 1]]
    )

    # Adjust hist to multiples of random distribution
    if use_multiples_of_random:
        random_point_density = np.sum(hist) / (np.pi * np.power(1, 2))
        hist_element_area = (xedges[1] - xedges[0]) * (yedges[1] - yedges[0])
        hist = hist / (random_point_density * hist_element_area)

    # Smooth histogram using a Gaussian filter
    if smooth_sigma is not None:
        hist = gaussian_filter(hist, smooth_sigma)

    # Set contour levels
    if isinstance(levels, int):
        vmax = np.ceil(np.quantile(hist, 0.99))
        nlevels = levels
        if vmax > 1.0:
            levels = np.linspace(1, vmax, nlevels)
        else:
            levels = np.array([1])
        if use_multiples_of_random:
            levels = np.insert(levels, 0, 0.75)
            levels = np.insert(levels, 0, 0.5)
            levels = np.insert(levels, 0, 0.25)
        else:
            levels = np.insert(levels, 0, 0)
    else:
        vmax = levels[-1]

    # Plot contours
    if ax is None:
        _, ax = plt.subplots()
    ax.contourf(
        hist,
        extent=(-1, 1, -1, 1),
        levels=levels,
        cmap="turbo",
        vmin=0,
        vmax=vmax,
        extend="both",
    )

    # Create mask
    xs = np.linspace(-1, 1, 1000)
    y0 = -np.ones_like(xs)
    y1 = np.ones_like(xs)
    yc_upper = np.where(xs <= 1, np.sqrt(1 - np.power(xs, 2)), 0)
    yc_lower = -yc_upper
    plt.fill_between(xs, y0, yc_lower, fc="w", ec="w")
    plt.fill_between(xs, yc_upper, y1, fc="w", ec="w")

    # Add border and format axes
    circle = plt.Circle((0.0, 0.0), 1.0, fc="none", ec="k", linewidth=3)
    ax.add_patch(circle)
    ax.set_title(f"{tuple(direction)}\n")
    ax.set_aspect(1)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-1.05, 1.05)
    ax.axis("off")
    if use_multiples_of_random:
        label = "MRD"
    else:
        label = "Count"
    if annotate_xy:
        ax.annotate("X", (1.05, 0), va="center", ha="left", size="large", weight="bold")
        ax.annotate(
            "Y", (0, 1.025), va="bottom", ha="center", size="large", weight="bold"
        )
    plt.colorbar(mappable=ax.collections[0], label=label)

    return ax
