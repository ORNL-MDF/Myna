import numpy as np
import pandas as pd
import pyebsd
from vtk.util.numpy_support import vtk_to_numpy
import time
from .subgrain import rotate_grains
from .vtk import vtk_structure_points_locs


# Get rotation vectors associated with each grain ID
def load_grain_ids(fileName):
    col_names = ["nx1", "nx2", "nx3", "ny1", "ny2", "ny3", "nz1", "nz2", "nz3"]
    dfIds = pd.read_csv(fileName, skiprows=1, header=None, names=col_names)
    dfIds["Grain ID"] = dfIds.index + 1
    dfIds["Grain ID"] = dfIds["Grain ID"].astype(int)

    # Convert <nx1, ny1, nz1, ...> to <phi1, Phi, phi2>
    dfIds["phi1"] = 0.0
    dfIds["Phi"] = 0.0
    dfIds["phi2"] = 0.0
    id_phi1 = dfIds.columns.get_loc("phi1")
    id_Phi = dfIds.columns.get_loc("Phi")
    id_phi2 = dfIds.columns.get_loc("phi2")
    col_ids = [dfIds.columns.get_loc(x) for x in col_names]
    R = dfIds.iloc[:, col_ids].to_numpy()
    R = R.reshape(len(R), 3, 3)
    phi1, Phi, phi2 = pyebsd.ebsd.orientation.rotation_matrix_to_euler_angles(
        R, conv="zxz"
    )
    dfIds.iloc[:, id_phi1] = phi1
    dfIds.iloc[:, id_Phi] = Phi
    dfIds.iloc[:, id_phi2] = phi2

    # Drop orientation vectors, i.e., col_names
    dfIds.drop(columns=col_names, inplace=True)

    return dfIds


# Convert Grain IDs to orientation vectors
def convert_id_to_rotation(
    vtk_reader, ref_id_file, misorientation=0.0, update_ids=False
):

    # Get dataframe of reference ids
    df_ids = load_grain_ids(ref_id_file)

    # Get the output of the reader
    structured_points = vtk_reader.GetStructuredPointsOutput()

    # Get the coordinates of all points
    x, y, z = vtk_structure_points_locs(structured_points)

    # Convert vtk data to dataframe
    gids = vtk_to_numpy(structured_points.GetPointData().GetArray("GrainID"))
    data = pd.DataFrame({"X (m)": x, "Y (m)": y, "Z (m)": z})

    # ID for orientation
    data["Grain ID"] = np.where(gids == 0, np.zeros_like(gids), np.mod(gids, 10000))
    data["Grain ID"] = data["Grain ID"].astype(int)

    # ID for parent grain
    data["gid"] = gids
    data["gid"] = data["gid"].astype(int)

    # Merge VTK and Grain ID DataFrames
    dfMerged = data.merge(df_ids, on="Grain ID", how="outer")
    dfMerged.drop(dfMerged.index[dfMerged["gid"].isna()], inplace=True)

    # Set new axes
    dfMerged["axis_dist"] = 0
    dfMerged["theta"] = 0

    # Get list of unique grains
    grains = dfMerged["gid"].unique()

    # Save reference orientations
    ref_cols = ["phi1", "Phi", "phi2"]
    ref_cols_ids = [dfMerged.columns.get_loc(x) for x in ref_cols]
    ref_or = df_ids[ref_cols].to_numpy()
    ref_id = df_ids["Grain ID"].to_numpy()

    # Sort list of grains by size
    t0 = time.perf_counter()
    group = dfMerged.groupby("gid")
    sorted_group = sorted(zip(group.size(), group.grouper.levels[0]), reverse=True)
    sizes = [x[0] for x in sorted_group]
    gids = [x[1] for x in sorted_group]
    t1 = time.perf_counter()

    # Calculate rotated grain orientation vectors
    if misorientation != 0.0:
        dfMerged = rotate_grains(
            dfMerged, gids, misorientation, update_ids, ref_or, ref_id, ref_cols_ids
        )

    return dfMerged
