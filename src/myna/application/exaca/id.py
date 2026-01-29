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
from vtk.util.numpy_support import vtk_to_numpy  # ty: ignore[unresolved-import]
from .subgrain import rotate_grains
from .vtk import vtk_structure_points_locs


def rotation_matrix_to_euler(R, frame="passive"):
    """Convert rotation matrices to the corresponding set of Euler angles in the Bunge
    ZXZ passive reference frame

    Adapted from D. Depriester, 2018.
    https://doi.org/10.13140/RG.2.2.34498.48321/5

    Args:
        R: [M,M] rotation matrix or [N,M,M] array of N rotation matrices
        frame: reference frame for the given rotation matrix, options are
               "passive" (matrix for sample frame rotating to crystal frame) or
               "active" (matrix for crystal frame rotating to sample frame)
    """

    # Set an arbitrary constant for when np.sin(Phi) == 0 and Phi == 0|pi
    const = 0

    # Ensure that R is a list of rotation matrices
    if np.ndim(R) == 2:
        R = np.array([R])

    # Calculate Euler angles
    if frame == "active":
        R = np.linalg.inv(R)
    g11 = R[:, 0, 0]
    g13 = R[:, 0, 2]
    g21 = R[:, 1, 0]
    g23 = R[:, 1, 2]
    g31 = R[:, 2, 0]
    g32 = R[:, 2, 1]
    g33 = R[:, 2, 2]
    Phi = np.arccos(g33)
    phi1 = np.where(
        np.sin(Phi) != 0,
        np.arctan2(g31, -g32),
        np.where(
            Phi == 0,
            np.arctan2(-g21, g11) - const,
            np.arctan2(g21, g11) + const,
        ),
    )
    phi2 = np.where(
        np.sin(Phi) != 0,
        np.arctan2(g13, g23),
        np.ones_like(Phi) * const,
    )
    phi1[phi1 < 0] = phi1[phi1 < 0] + 2.0 * np.pi
    phi2[phi2 < 0] = phi2[phi2 < 0] + 2.0 * np.pi
    return phi1, Phi, phi2


# Get rotation vectors associated with each reference ID
def load_grain_ids(fileName):
    col_names = ["nx1", "ny1", "nz1", "nx2", "ny2", "nz2", "nx3", "ny3", "nz3"]
    dfIds = pd.read_csv(fileName, skiprows=1, header=None, names=col_names)
    dfIds["Reference ID"] = dfIds.index
    dfIds["Reference ID"] = dfIds["Reference ID"].astype(int)

    # Convert <nx1, ny1, nz1, ...> to <phi1, Phi, phi2>
    dfIds["phi1"] = 0.0
    dfIds["Phi"] = 0.0
    dfIds["phi2"] = 0.0
    rot_col_ids = [dfIds.columns.get_loc(x) for x in col_names]
    R = dfIds.iloc[:, rot_col_ids].to_numpy()
    R = R.reshape(len(R), 3, 3)
    phi1, Phi, phi2 = rotation_matrix_to_euler(R, frame="passive")

    # Store Euler angles in dataframe
    id_phi1 = dfIds.columns.get_loc("phi1")
    id_Phi = dfIds.columns.get_loc("Phi")
    id_phi2 = dfIds.columns.get_loc("phi2")
    dfIds.iloc[:, id_phi1] = phi1
    dfIds.iloc[:, id_Phi] = Phi
    dfIds.iloc[:, id_phi2] = phi2

    # Drop orientation vectors, i.e., col_names
    # dfIds.drop(columns=col_names, inplace=True)

    return dfIds


def grain_id_to_reference_id(grain_ids, num_ref_ids):
    """Converts ExaCA grain IDs to the reference orientation ID

    Args:
        grain_ids: list-like of grain ids
        num_ref_ids: number of reference orientations (e.g., rows in reference file)
    """
    grain_ids = np.array(grain_ids)
    ref_ids = np.where(
        grain_ids == 0,
        np.zeros_like(grain_ids),
        np.mod(np.abs(grain_ids) - 1, num_ref_ids),
    )
    return ref_ids


# Convert Grain IDs to orientation vectors using a list of reference IDs
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
    data["Reference ID"] = grain_id_to_reference_id(gids, len(df_ids))
    data["Reference ID"] = data["Reference ID"].astype(int)

    # ID for parent grain
    data["Grain ID"] = gids
    data["Grain ID"] = data["Grain ID"].astype(int)

    # Merge VTK and Reference ID DataFrames
    dfMerged = data.merge(df_ids, on="Reference ID", how="outer")
    dfMerged.drop(dfMerged.index[dfMerged["Grain ID"].isna()], inplace=True)

    # Set new axes
    dfMerged["axis_dist"] = 0
    dfMerged["theta"] = 0

    # Save reference orientations
    ref_cols = ["phi1", "Phi", "phi2"]
    ref_cols_ids = [dfMerged.columns.get_loc(x) for x in ref_cols]
    ref_or = df_ids[ref_cols].to_numpy()
    ref_id = df_ids["Reference ID"].to_numpy()

    # Sort list of grains by size
    group = dfMerged.groupby("Grain ID")
    sorted_group = sorted(zip(group.size(), group.grouper.levels[0]), reverse=True)
    gids = [x[1] for x in sorted_group]

    # Calculate rotated grain orientation vectors
    if misorientation != 0.0:
        dfMerged = rotate_grains(
            dfMerged, gids, misorientation, update_ids, ref_or, ref_id, ref_cols_ids
        )

    return dfMerged
