#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from scipy.stats import iqr, wasserstein_distance
import pandas as pd
import numpy as np
import math


def get_mean_grain_area(df2D, cell_size, threshold_grain_size=6):
    """Returns mean grain area, filtering out grains smaller than a threshold

    Args:
        df2D: dataframe corresponding to a 2D slice of a 3D grain structure
        cell_size: spacing of pixels in the dataframe
        threshold_grain_size: size below which grains are too small to be
        included in the average calculation

    Returns:
        mean_grain_area: in square meters
    """
    # Get unique grains and their value counts
    grains = df2D["Grain ID"].value_counts()

    # Subset of the grains with sizes less than a threshold size
    small_grain_pixels = sum(grains[grains.values < threshold_grain_size])
    # Subset of the grains with sizes of at least the "critical" size
    large_grain_pixels = grains[grains.values >= threshold_grain_size]
    # Pixels from small grains will be reassigned unifomly to the other grains
    added_grain_area = small_grain_pixels / len(large_grain_pixels)
    large_grain_pixels = large_grain_pixels + added_grain_area
    # Mean grain area, converted to square meters
    mean_grain_area = cell_size * cell_size * np.mean(large_grain_pixels)
    return mean_grain_area


def get_fract_nucleated_grains(df2D):
    """Returns the fraction of grains formed via nucleation event

    Args:
        df2D: dataframe corresponding to a 2D slice of a 3D grain structure

    Returns:
        fract_nucleated_grains: fraction of grains in the 2D slice formed via
        nucleation event (denoted with a negative grain ID). Note that the
        very small grains thresholded out in the mean area calculation are not
        filtered out here - but could be in the future
    """
    fract_nucleated_grains = len(df2D[df2D["Grain ID"] < 0]) / len(df2D)
    return fract_nucleated_grains


def get_misorientation_z_ref(reference_id_filename):
    """From the file of grain orientations, return a list of misorientations
    between a grain orientation's nearest <100> and the Z axis
    Args:
        reference_id_filename: name of file containing rotation matrices to be
        mapped to each grain_id

    Returns:
        misorientation_z_ref: np array of misorientation values, in degrees
        for each possible grain orientation in the file"""
    # misorientation_z could be stored in the df after grain orientation bug
    # is fixed
    col_names = ["nx1", "ny1", "nz1", "nx2", "ny2", "nz2", "nx3", "ny3", "nz3"]
    dfRefIds = pd.read_csv(
        reference_id_filename, skiprows=1, header=None, names=col_names
    )
    num_reference_ids = len(dfRefIds)
    misorientation_z_ref = np.zeros(num_reference_ids)
    # Z components of the three unit vectors defining the crystal orientation
    nz1 = abs(dfRefIds["nz1"])
    nz2 = abs(dfRefIds["nz2"])
    nz3 = abs(dfRefIds["nz3"])
    # Calculate <100> misorientation with Z and append to dataframe
    for i in range(num_reference_ids):
        if (nz1[i] >= nz2[i]) and (nz1[i] >= nz3[i]):
            misorientation_z_ref[i] = math.degrees(math.acos(nz1[i]))
        elif (nz2[i] >= nz1[i]) and (nz2[i] >= nz3[i]):
            misorientation_z_ref[i] = math.degrees(math.acos(nz2[i]))
        else:
            misorientation_z_ref[i] = math.degrees(math.acos(nz3[i]))
    return misorientation_z_ref


def get_misorientation_z(df, misorientation_z_ref):
    """args:
        df: dataframe containing "Grain ID" values
        misorientation_z_ref: np array of misorientation values, in degrees,
        for each possible grain orientation

    Returns:
        misorientation_z_list: np array of misorientation values, in degrees,
        for each cell in the df"""
    # Absolute value of grain ID used for conversion
    gid_abs = abs(df["Grain ID"].values)
    num_gid_values = len(gid_abs)
    misorientation_z_list = np.zeros(num_gid_values)
    num_reference_ids = len(misorientation_z_ref)
    # gid_index can be replaced with the stored grain id value
    # from the df after indexing bug is fixed
    for i in range(num_gid_values):
        gid_index = int((gid_abs[i] - 1) % num_reference_ids)
        misorientation_z_list[i] = misorientation_z_ref[gid_index]
    return misorientation_z_list


def get_bin_centers_fre_dia(df2D, misorientation_z_list):
    """Freedman–Diaconis rule for bin width calculation based on the skewed
    nature of both the untextured and actual misorientation distributions
    Bin data based on the number of unique grains in the data
    Args:
        df: dataframe containing "Grain ID" values
        misorientation_z_list: list of grain misorientations with <100>, in
        degrees, used to map gid values

    Returns:
        bin_edges: edges for binned misorientation data
        bin_centers: center location of bins for misorientation data"""
    num_grains = len(df2D["Grain ID"].unique())
    bin_width_ideal = 2 * iqr(misorientation_z_list) / (num_grains ** (1 / 3))
    # Get edges of bins for misorientation data (0 to 54.7 degrees)
    num_bins = round(54.7 / bin_width_ideal)
    bin_width = 54.7 / num_bins
    bin_edges = [None] * (num_bins + 1)
    for i in range(num_bins + 1):
        bin_edges[i] = i * bin_width
    # Get bin centers
    bin_centers = [None] * num_bins
    for i in range(num_bins):
        bin_centers[i] = bin_edges[i] + bin_width / 2
    return [bin_edges, bin_centers]


def get_wasserstein_distance_misorientation_z(df, ref_file):
    """Calculate the distance between the orientations in a 2D slice of Euler angles
    and a randomly oriented, isotropic reference

    Args:
        df: DataFrame containing Grain ID values
        ref_file: Reference file containing orientation IDs"""
    misorientation_z_ref = get_misorientation_z_ref(ref_file)
    misorientation_z_list = get_misorientation_z(df, misorientation_z_ref)
    [bin_edges, bin_centers] = get_bin_centers_fre_dia(df, misorientation_z_list)
    counts_ref, _ = np.histogram(misorientation_z_ref, bins=bin_edges, density=True)
    counts_list, _ = np.histogram(misorientation_z_list, bins=bin_edges, density=True)

    # Wasserstein distance between the two distributions
    wasserstein = wasserstein_distance(
        bin_centers, bin_centers, counts_ref, counts_list
    )
    return wasserstein
