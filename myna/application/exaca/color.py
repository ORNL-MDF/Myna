import numpy as np
import pyebsd


# Get RGB values for each orientation
def add_pyebsd_rgb_color(df, refDir=[0, 0, 1], suffix=""):
    # Initialize rotation matrix array and put Euler-Bunge angles in correct order for pyebsd
    ref_cols = ["phi1", "Phi", "phi2"]
    ref_cols_ids = [df.columns.get_loc(x) for x in ref_cols]
    R = pyebsd.ebsd.orientation.euler_angles_to_rotation_matrix(
        df.iloc[:, ref_cols_ids[0]],
        df.iloc[:, ref_cols_ids[1]],
        df.iloc[:, ref_cols_ids[2]],
        conv="zxz",
    )
    orientation = pyebsd.ebsd.orientation.IPF(R, refDir)

    # Convert rotation matrices (orientation) to RGB colors
    color = np.full((len(orientation), 4), 255, dtype=int)
    color[:, :3] = pyebsd.ebsd.plotting.get_color_IPF(orientation)

    # Set grain color
    df[f"R{suffix}"] = color[:, 0] / 255
    df[f"G{suffix}"] = color[:, 1] / 255
    df[f"B{suffix}"] = color[:, 2] / 255

    return df
