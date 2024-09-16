#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define grain statistics data
"""
import math
import myna.application.exaca
import pandas as pd
from scipy.stats import iqr
from scipy.stats import wasserstein_distance
import vtk
from vtk.util.numpy_support import vtk_to_numpy

def get_values_for_sync(grain_id_file, reference_id_filename, z_cross_loc):
    """Get values in format expected from sync

    Args:
        grain_id_file: filename of vtk grain id data
        reference_id_filename: file name for csv grain orientation data
        z_cross_loc: cross-section in meters corresponding to the grain
        structure data of interest

    Returns:
        dataset: pandas dataframe containing x,y,v1,v2,v3 data, where v1,v2,v3
        are the mean grain area, the fraction of nucleated grains, and the
        Wasserstein distance between the distribution of grain misorientations
        of <100> with Z comapred to the reference orientation data
    """
    # Read the VTK file
    reader = vtk.vtkDataSetReader()
    reader.SetFileName(grain_id_file)
    reader.ReadAllScalarsOn()
    reader.Update()
    structured_points = reader.GetOutput()
    spacing = structured_points.GetSpacing()

    # Convert grain ids into Euler angles
    df = myna.application.exaca.convert_id_to_rotation(reader, reference_id_filename)
    
    # Downselect the 2D data at z_cross_loc from the 3D dataframe
    # Use tolerance to avoid floating point comparison error
    df2D = df[abs(df["Z (m)"] - z_cross_loc) < 1e-9]
    
    # Get mean grain area
    mean_grain_area = get_mean_grain_area(df2D, spacing[0])
    # Get fraction of grains formed via nucleation events
    fraction_nucleated_grains = get_fract_nucleated_grains(df2D)
    # Get bins and counts for Wasserstein distance calcualtion for grain <100>
    # misorientation with respect to the Z direction
    # <100> misorientation with Z for the reference orientations
    misorientation_z_ref = get_misorientation_z_ref(reference_id_filename)
    # Map gid values from 2D data to the list of <100> misorientations with Z
    misorientation_z_list = get_misorientation_z(df2D, misorientation_z_ref)
    # Get bins for misorientation data
    [bin_edges, bin_centers] = get_bin_centers_fre_dia(df2D, 
         misorientation_z_list)
    # Histogram for misorientation with respect to the untextured reference
    counts_ref, bins_a, bars_a = plt.hist(misorientation_z_ref, bins=bin_edges,
         color="blue", alpha=0.5, density=True)
    counts_list, bins_b, bars_b = plt.hist(misorientation_z_list, 
         bins=bin_edges, color="red", alpha=0.5, density=True)
    # Wasserstein distance between the two distributions
    wasserstein_distance_misorientation_z = wasserstein_distance(bin_centers, 
         bin_centers, counts_ref, counts_list)
    
    # List of points
    x, y, z = vtk_structure_points_locs(structured_points)
    num_points = len(x)
    mean_grain_area_df = np.full(num_points, mean_grain_area)
    fraction_nucleated_grains_df = np.full(num_points, fraction_nucleated_grains)
    wasserstein_distance_df = np.full(num_points, wasserstein_distance_misorientation_z)
    dataset = pd.DataFrame({'x': x, 'y': y, 'Mean grain area': mean_grain_area_df, 
         'Fraction nucleated grains': fraction_nucleated_grains_df, 
         'Wasserstein distance Z misorientation distribution': wasserstein_distance_df})
    return dataset

    
def get_mean_grain_area(df2D, cell_size, threshold_grain_size = 6):
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
    grains = df2D["gid"].value_counts()
    
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
    fract_nucleated_grains = len(df2D[df2D["gid"] < 0]) / len(df2D)
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
    dfRefIds = pd.read_csv(reference_id_filename, skiprows=1, header=None, 
        names=col_names)
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
        df: dataframe containing gid values
        misorientation_z_ref: np array of misorientation values, in degrees, 
        for each possible grain orientation

    Returns:
        misorientation_z_list: np array of misorientation values, in degrees,
        for each cell in the df"""
    # Absolute value of grain ID used for conversion
    gid_abs = abs(df["gid"].values)
    num_gid_values = len(gid_abs)
    misorientation_z_list = np.zeros(num_gid_values)
    num_reference_ids = len(misorientation_z_ref)
    # gid_index can be replaced with the stored gid value 
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
        df: dataframe containing gid values
        misorientation_z_list: list of grain misorientations with <100>, in
        degrees, used to map gid values

    Returns:
        bin_edges: edges for binned misorientation data
        bin_centers: center location of bins for misorientation data"""
    num_grains = len(df2D["gid"].unique())
    bin_width_ideal = 2 * iqr(misorientation_z_list) / (num_grains ** (1/3))
    # Get edges of bins for misorientation data (0 to 54.7 degrees)
    num_bins = round(54.7 / bin_width_ideal)
    bin_width = 54.7 / num_bins
    bin_edges = [None] * (num_bins+1)
    for i in range(num_bins+1):
        bin_edges[i] = i * bin_width
    # Get bin centers
    bin_centers = [None] * num_bins
    for i in range(num_bins):
        bin_centers[i] = bin_edges[i] + bin_width / 2
    return [bin_edges, bin_centers]
