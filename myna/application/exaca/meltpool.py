#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import polars as pl
import numpy as np
import json
import vtk
import os
from vtk.util.numpy_support import numpy_to_vtkIdTypeArray, numpy_to_vtk, vtk_to_numpy
from .vtk import *
from myna.core.utils import nested_get


def aggregate_melt_times(
    exaca_input, export_name="melt_time.vtu", verbose=False, decimal_precision=8
):

    # Get input settings
    with open(exaca_input, "r") as f:
        input_settings = json.load(f)

    # Get list of solidification data files and layer offset
    files = sorted(nested_get(input_settings, ["TemperatureData", "TemperatureFiles"]))
    layer_offset = (
        1e-6
        * nested_get(input_settings, ["Domain", "CellSize"])
        * nested_get(input_settings, ["Domain", "LayerOffset"])
    )

    # Get representative file size, in bytes
    filesize = os.path.getsize(files[0])

    # Aggregate the data, pruning to last solidification time for every `chunk_size`
    # of temperature files loaded
    chunk_size = 2e9
    files_per_chunk = max(int(np.round(chunk_size / filesize, 0)), 1)
    if verbose:
        print("\nFile loading information:\n")
        print(f"- first filesize = {filesize/1e9:.3f} GB")
        print(f"- chunk size = {chunk_size/1e9:.3f} GB")
        print(f"- files per chunk = {files_per_chunk}")
    df_all = None
    ts_max = 0
    if verbose:
        print("\nReading files:\n")

    for i, f in enumerate(files):

        if verbose:
            print(f"- {i+1}/{len(files)}: {f}")

        df = pl.read_csv(
            f,
            dtypes=[
                pl.Float64,
                pl.Float64,
                pl.Float64,
                pl.Float64,
                pl.Float64,
                pl.Float64,
            ],
        )

        # Adjust time to account for previous layers
        df = df.with_columns((pl.col("ts") + ts_max).alias("ts"))
        ts_max = df["ts"].max()

        # Shift in Z-direction
        df = df.with_columns((pl.col("z") + i * layer_offset).alias("z"))

        # Only consider the last solidification event
        df = df.group_by(["x", "y", "z"]).agg(pl.col("ts").max())
        df = df.with_columns((pl.col("x").round(decimal_precision)).alias("x"))
        df = df.with_columns((pl.col("y").round(decimal_precision)).alias("y"))
        df = df.with_columns((pl.col("z").round(decimal_precision)).alias("z"))

        # Append to other layers
        if df_all is None:
            df_all = df
        else:
            df_all = df_all.vstack(df)

        # Reduce data as specific by chunksize
        if i % files_per_chunk == 0:
            df_all.rechunk()
            df_all = df_all.group_by(["x", "y", "z"]).agg(pl.col("ts").max())

    # Finally, ensure that only the last solidification event is stored
    df_all.rechunk()
    df_all = df_all.group_by(["x", "y", "z"]).agg(pl.col("ts").max())

    if verbose:
        print("\nCalculating:\n")

    # Sort and take difference of ts in x-direction
    if verbose:
        print("- dts_x")
    df_all = df_all.sort(["z", "y", "x"], descending=False)
    ts = df_all["ts"].to_numpy()
    dts_x = np.array([0])
    dts_x = np.append(dts_x, ts[1:] - ts[:-1])
    df_all = df_all.with_columns(
        (pl.Series(name="dts_x", values=dts_x).abs()).alias("dts_x")
    )

    # Sort and take difference of ts in y-direction
    if verbose:
        print("- dts_y")
    df_all = df_all.sort(["z", "x", "y"], descending=False)
    ts = df_all["ts"].to_numpy()
    dts_y = np.array([0])
    dts_y = np.append(dts_y, ts[1:] - ts[:-1])
    df_all = df_all.with_columns(
        (pl.Series(name="dts_y", values=dts_y).abs()).alias("dts_y")
    )

    # Sort and take difference of ts in z-direction
    if verbose:
        print("- dts_z")
    df_all = df_all.sort(["y", "x", "z"], descending=False)
    ts = df_all["ts"].to_numpy()
    dts_z = np.array([0])
    dts_z = np.append(dts_z, ts[1:] - ts[:-1])
    df_all = df_all.with_columns(
        (pl.Series(name="dts_z", values=dts_z).abs()).alias("dts_z")
    )

    # Drop x == xmin, which will have incorrect gradients
    if verbose:
        print("- cleaning")
    df_all = df_all.filter(df_all["x"] > df_all["x"].min())
    df_all = df_all.filter(df_all["y"] > df_all["y"].min())

    if verbose:
        print("\nPreparing VTK file:\n")

    # Convert Polars DataFrame to numpy arrays
    if verbose:
        print("- converting dataframe columns to arrays")
    points_array = df_all[["x", "y", "z"]].to_numpy().astype(np.float64)
    vectors_array = df_all[["dts_x", "dts_y", "dts_z"]].to_numpy().astype(np.float64)
    scalars_array = df_all["ts"].to_numpy().astype(np.float64)

    # Create point data object
    if verbose:
        print("- adding points")
    points = vtk.vtkPoints()
    vtk_points = numpy_to_vtk(points_array)
    points.SetData(vtk_points)

    # Create vector data object
    if verbose:
        print("- adding vectors")
    vectors = vtk.vtkFloatArray()
    vectors.SetNumberOfComponents(3)
    vtk_vectors = numpy_to_vtk(vectors_array.reshape(-1, 3))
    vectors.DeepCopy(vtk_vectors)
    vectors.SetName("dts")

    # Create scalar data object
    if verbose:
        print("- adding scalars")
    scalars = vtk.vtkFloatArray()
    vtk_scalars = numpy_to_vtk(scalars_array)
    scalars.DeepCopy(vtk_scalars)
    scalars.SetName("ts")

    # Create vtkUnstructuredGrid object
    if verbose:
        print("- creating grid")
    unstructured_grid = vtk.vtkUnstructuredGrid()
    unstructured_grid.SetPoints(points)

    # Create vertices for the unstructured grid and set to grid
    if verbose:
        print("- creating vertices")
    vertices = vtk.vtkCellArray()
    num_points = len(points_array)
    vertex_data = np.zeros((num_points, 2), dtype=np.int64)
    vertex_data[:, 0] = 1
    vertex_data[:, 1] = np.arange(num_points)
    vtk_vertex_data = numpy_to_vtkIdTypeArray(vertex_data.ravel(), deep=True)
    vertices.SetCells(vtk.VTK_VERTEX, vtk_vertex_data)
    unstructured_grid.SetCells(vtk.VTK_VERTEX, vertices)

    # Set vectors and scalars to the point data
    if verbose:
        print("- setting data")
    unstructured_grid.GetPointData().SetVectors(vectors)
    unstructured_grid.GetPointData().SetScalars(scalars)

    # Write to a .vtu file
    if verbose:
        print(f"- writing file {export_name}")
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(export_name)
    writer.SetInputData(unstructured_grid)
    writer.SetDataModeToBinary()  # Set to binary mode
    writer.Write()


def merge_melt_times_with_rgb(
    file_rgb, file_melt, export_file, decimal_precision=8, verbose=False
):

    if verbose:
        print("\nLoading data:\n")

    # Read the RGB file
    if verbose:
        print("- loading ExaCA VTK file with RGB coloring")
    vtk_rgb_reader = grain_id_reader(file_rgb)
    vtk_rgb_data = vtk_rgb_reader.GetOutput()
    dims = vtk_rgb_data.GetDimensions()
    origin = vtk_rgb_data.GetOrigin()
    spacing = vtk_rgb_data.GetSpacing()
    bounds = vtk_rgb_data.GetBounds()
    if verbose:
        print(f"- loaded ExaCA VTK data: {type(vtk_rgb_data)}")

    # Read the melt times file
    if verbose:
        print("- loading AdditiveFOAM VTK file with melt times")
    vtk_melt_reader = vtk.vtkXMLUnstructuredGridReader()
    vtk_melt_reader.SetFileName(file_melt)
    vtk_melt_reader.Update()
    vtk_melt_data = vtk_melt_reader.GetOutput()
    if verbose:
        print(f"- loaded AdditiveFOAM VTK data: {type(vtk_melt_data)}")

    # Convert RGB vtk data to dataframe
    if verbose:
        print(f"- converting ExaCA VTK data to dataframe")
    gids = vtk_to_numpy(vtk_rgb_data.GetPointData().GetArray("Grain ID"))
    rgbZ = vtk_to_numpy(vtk_rgb_data.GetPointData().GetVectors("rgbZ"))
    rz = rgbZ[:, 0]
    gz = rgbZ[:, 1]
    bz = rgbZ[:, 2]
    x, y, z = vtk_structure_points_locs(vtk_rgb_data)
    data_rgb = pl.DataFrame(
        {"X (m)": x, "Y (m)": y, "Z (m)": z, "RZ": rz, "GZ": gz, "BZ": bz}
    )
    data_rgb = data_rgb.with_columns(
        (pl.col("X (m)").round(decimal_precision)).alias("X (m)")
    )
    data_rgb = data_rgb.with_columns(
        (pl.col("Y (m)").round(decimal_precision)).alias("Y (m)")
    )
    data_rgb = data_rgb.with_columns(
        (pl.col("Z (m)").round(decimal_precision)).alias("Z (m)")
    )
    grain_ids = np.where(gids == 0, np.zeros_like(gids), np.mod(gids, 10000))

    # ID for orientation ("Grain ID") and parent grain ("gid")
    data_rgb = data_rgb.with_columns(pl.Series(name="Grain ID", values=grain_ids))
    data_rgb = data_rgb.with_columns(pl.Series(name="gid", values=gids))
    data_rgb = data_rgb.cast({"Grain ID": int, "gid": int})

    # Convert melt vtk data to dataframe
    if verbose:
        print(f"- converting melt VTK data to dataframe")
    x, y, z = vtk_unstructured_grid_locs(vtk_melt_data)
    dts = np.linalg.norm(
        vtk_to_numpy(vtk_melt_data.GetPointData().GetVectors("dts")), axis=1
    )
    ts = vtk_to_numpy(vtk_melt_data.GetPointData().GetArray("ts"))
    data_melt = pl.DataFrame({"X (m)": x, "Y (m)": y, "Z (m)": z, "ts": ts, "dts": dts})
    data_melt = data_melt.with_columns(
        (pl.col("X (m)").round(decimal_precision)).cast(pl.Float64).alias("X (m)")
    )
    data_melt = data_melt.with_columns(
        (pl.col("Y (m)").round(decimal_precision)).cast(pl.Float64).alias("Y (m)")
    )
    data_melt = data_melt.with_columns(
        (pl.col("Z (m)").round(decimal_precision)).cast(pl.Float64).alias("Z (m)")
    )

    # Filter vtk_melt to ExaCA (sub)domain
    if verbose:
        print(f"- cropping melt data")
    data_melt = data_melt.filter(pl.col("X (m)") >= bounds[0])
    data_melt = data_melt.filter(pl.col("X (m)") <= bounds[1])
    data_melt = data_melt.filter(pl.col("Y (m)") >= bounds[2])
    data_melt = data_melt.filter(pl.col("Y (m)") <= bounds[3])
    data_melt = data_melt.filter(pl.col("Z (m)") >= bounds[4])
    data_melt = data_melt.filter(pl.col("Z (m)") <= bounds[5])

    # Merge VTK-ID dataframe and Melt dataframe
    if verbose:
        print(f"- merging dataframes")
        print(f"  - data_rgb size: {data_rgb.shape}")
        print(f"  - data_melt size: {data_melt.shape}")
    df_merged = data_rgb.join(data_melt, on=["X (m)", "Y (m)", "Z (m)"], how="full")
    print(f"  - df_merged size (pre-gid-filter): {df_merged.shape}")
    df_merged = df_merged.filter(
        (pl.col("gid").is_not_null() & pl.col(["gid"]).is_not_nan())
    )
    print(f"  - df_merged size (post-gid-filter): {df_merged.shape}")
    df_merged = df_merged.sort(by=["Z (m)", "Y (m)", "X (m)"])

    # Create VTK dataset
    if verbose:
        print(f"\nAdding data to VTK file:\n")
    if verbose:
        print(f"- creating vtkStructuredPoints")
    vtk_dataset = vtk.vtkStructuredPoints()
    vtk_dataset.SetDimensions(dims)
    vtk_dataset.SetSpacing(spacing)
    vtk_dataset.SetOrigin(origin)

    # Add points
    if verbose:
        print(f"- adding points")
    points_array = df_merged[["Z (m)", "Y (m)", "X (m)"]].to_numpy().astype(np.float64)
    points = vtk.vtkPoints()
    vtk_points = numpy_to_vtk(points_array)
    points.SetData(vtk_points)

    # Add scalar data to vtk_dataset from df_merged
    scalar_names = ["gid", "ts", "dts"]
    scalar_types = [
        vtk.VTK_INT,
        vtk.VTK_FLOAT,
        vtk.VTK_FLOAT,
    ]
    for col, val_type in zip(scalar_names, scalar_types):
        if verbose:
            print(f"- adding scalar {col} ({val_type})")
        vtk_data = numpy_to_vtk(
            num_array=df_merged[col].to_numpy(), array_type=val_type
        )
        vtk_data.SetName(col)
        vtk_dataset.GetPointData().AddArray(vtk_data)

    # Add data as vector to VTK dataset
    # <"RZ", "GZ", "BZ">
    if verbose:
        print(f"- adding rgbZ vector data")
    cols = [f"RZ", f"GZ", f"BZ"]
    vtk_data = numpy_to_vtk(
        num_array=df_merged[cols].to_numpy(), deep=True, array_type=vtk.VTK_FLOAT
    )
    vtk_data.SetName(f"rgbZ")
    vtk_dataset.GetPointData().AddArray(vtk_data)

    # Write file using VTK file writer
    if verbose:
        print(f"- writing file {export_file}")
    writer = vtk.vtkDataSetWriter()
    writer.SetFileName(export_file)
    writer.SetInputData(vtk_dataset)
    writer.SetFileTypeToBinary()
    writer.Write()
