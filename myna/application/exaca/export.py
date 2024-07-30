import vtk
from vtk.util.numpy_support import numpy_to_vtk
from .color import add_pyebsd_rgb_color
from .id import convert_id_to_rotation
import numpy as np


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
        lookup_name: path to the lookup table of grain ID orientations (e.g., GrainOrientationVectors.csv)
    """

    # Read the VTK file
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(vtk_file_path)
    reader.ReadAllScalarsOn()
    reader.Update()
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
    scalar_names = ["gid", "Grain ID"]
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
