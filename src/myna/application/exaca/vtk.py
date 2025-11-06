#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import numpy as np
import pandas as pd
from vtk.util.numpy_support import vtk_to_numpy
from vtk import vtkDataSetReader


def grain_id_reader(grain_id_file):
    """Returns the VTK reader for the grain ID file

    Args:
        grain_id_file: path to grain ID file output by an ExaCA simulation

    Returns:
        vtkDatasetReader
    """
    reader = vtkDataSetReader()
    reader.SetFileName(grain_id_file)
    reader.ReadAllScalarsOn()
    reader.Update()

    return reader


def vtk_structure_points_locs(structured_points):
    """Returns arrays of x, y, and z coordinates for all points

    Args:
        structured_points: vtkStructuredPoints object

    Returns:
        x: x-coordinates as a numpy array
        y: y-coordinates as a numpy array
        z: z-coordinates as a numpy array
    """

    # Get dimensions, origin, and spacing
    dims = structured_points.GetDimensions()
    origin = structured_points.GetOrigin()
    spacing = structured_points.GetSpacing()

    # Generate the coordinates based on dimensions, origin, and spacing
    xs = np.linspace(origin[0], origin[0] + (dims[0] - 1) * spacing[0], dims[0])
    ys = np.linspace(origin[1], origin[1] + (dims[1] - 1) * spacing[1], dims[1])
    zs = np.linspace(origin[2], origin[2] + (dims[2] - 1) * spacing[2], dims[2])

    # Create meshgrid for the structured points and flatten
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    df_points = pd.DataFrame(
        {
            "x": X.flatten(),
            "y": Y.flatten(),
            "z": Z.flatten(),
        }
    )
    df_points.sort_values(by=["z", "y", "x"], inplace=True)
    x = df_points["x"].to_numpy()
    y = df_points["y"].to_numpy()
    z = df_points["z"].to_numpy()

    return [x, y, z]


def vtk_unstructured_grid_locs(unstructured_grid):
    """Returns arrays of x, y, and z coordinates for all points

    Args:
        unstructured_grid: vtkUnstructuredGrid object

    Returns:
        x: x-coordinates as a numpy array
        y: y-coordinates as a numpy array
        z: z-coordinates as a numpy array
    """

    # Extract points
    points_vtk = unstructured_grid.GetPoints().GetData()

    # Convert VTK points to a NumPy array
    points_np = vtk_to_numpy(points_vtk)

    # Split into X, Y, and Z arrays
    x = points_np[:, 0]
    y = points_np[:, 1]
    z = points_np[:, 2]

    return [x, y, z]
