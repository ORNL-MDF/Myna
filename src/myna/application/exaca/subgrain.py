#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import numpy as np
import time


def rotate_grains(
    dfMerged, gids, misorientation, update_ids, ref_or, ref_id, ref_cols_ids
):
    """Given a pandas DataFrame with Euler angles `phi1`, `Phi`, and `phi2`, rotate each
    grain voxel by the specified misorientation rate

    Args:
        dfMerged: (pandas DataFrame) DataFrame containing at least,
            `X (m)`, `Y (m)`, `Z (m)`, `phi1`, `Phi`, and `phi2`
        gids: (list of int) list of grain IDs contained within `dfMerged` to which to
            apply the misorientations
        misorientation: (float) misorientation rate (angle/meter) in the same angular
            units as `phi1`, with standard for ExaCA being degrees
        update_ids: (bool) whether to update the IDs of each voxel to match to closest
            ID to their new orientation
        ref_or: (numpy array) (N, 3) array of `phi1`, `Phi`, `phi2` of the reference
            orientations, with default ExaCA being N=10000
        ref_id: (numpy array) (N, 1) array of `Reference ID` of the reference
            orientations, with default ExaCA being N=10000
        ref_cols_ids: (list of ints) array of column indices for `phi1`, `Phi`, and
            `phi2` in `dfMerged`
    """

    for grain_index, gid in enumerate(gids):
        # Print progress
        print(f"Rotating grain index {gid} ({grain_index} of {len(gids)})")
        t0 = time.perf_counter()

        # Get grain points
        if gid == 0:
            continue
        grain_indices = dfMerged[dfMerged["Grain ID"] == gid].index
        if len(grain_indices) < 100:
            continue
        print(f"\tProcessing {len(grain_indices)} grains")
        col_ids = [dfMerged.columns.get_loc(x) for x in ["X (m)", "Y (m)", "Z (m)"]]
        t1 = time.perf_counter()

        # Calculate distance along rotation axis (Z)
        col_id = dfMerged.columns.get_loc("Z (m)")
        lengths = (
            dfMerged.iloc[grain_indices, col_id].to_numpy()
            - dfMerged.iloc[grain_indices, col_id].min()
        )

        # Rotate grain orientation vectors (v) around major axis unit vector (k)
        # by angle (theta, radians) using Rodrigues' rotation formula
        thetas = np.radians(lengths * misorientation)
        t2 = time.perf_counter()
        bd = np.array([0, 0, 1])
        k = bd / np.linalg.norm(bd)
        col_id = dfMerged.columns.get_loc("phi2")
        dfMerged.iloc[grain_indices, col_id] = (
            dfMerged.iloc[grain_indices, col_id].to_numpy() + thetas
        )
        t3 = time.perf_counter()

        # Update Reference IDs in merged DataFrame to match the
        # rotated grain orientation vectors (if specified)
        if update_ids:
            chunk_size = 25000
            step = 0
            while step * chunk_size <= len(grain_indices):
                i0 = step * chunk_size
                i1 = (step + 1) * chunk_size
                print(f"\tUpdating grain id ({i0}-{i1} of {len(grain_indices)})")

                # Construct array for rotated grain orientation vectors and reference vectors
                if i1 >= len(grain_indices):
                    orientation_vectors = dfMerged.iloc[
                        grain_indices[i0:], ref_cols_ids
                    ].to_numpy()
                else:
                    orientation_vectors = dfMerged.iloc[
                        grain_indices[i0:i1], ref_cols_ids
                    ].to_numpy()
                orientation_vectors = np.repeat(
                    orientation_vectors[np.newaxis, :], len(ref_or), axis=0
                )
                reference_vectors = np.repeat(
                    ref_or[:, np.newaxis, :], orientation_vectors.shape[1], axis=1
                )

                # Calculate difference between rotated grain orientation vectors and reference vectors
                diff = orientation_vectors - reference_vectors
                norms = np.linalg.norm(diff, axis=2).T

                # Find index of minimum difference for each rotated grain orientation vector
                min_indices = np.argmin(norms, axis=1)

                # Update reference IDs in merged DataFrame
                col_id = dfMerged.columns.get_loc("Reference ID")
                if i1 >= len(grain_indices):
                    dfMerged.iloc[grain_indices[i0:], col_id] = ref_id[min_indices]
                else:
                    dfMerged.iloc[grain_indices[i0:i1], col_id] = ref_id[min_indices]
                step += 1

            t4 = time.perf_counter()

            # Save rotated vectors to merged DataFrame
            col_id = dfMerged.columns.get_loc("axis_dist")
            dfMerged.iloc[grain_indices, col_id] = lengths
            col_id = dfMerged.columns.get_loc("theta")
            dfMerged.iloc[grain_indices, col_id] = np.degrees(thetas)
            t5 = time.perf_counter()
            print(f"\tTime to perform grain rotations: {t5 - t0} s")
