#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import numpy as np


def downsample_to_image(
    data_x, data_y, values, image_size, plate_size, bottom_left=[0, 0], mode="max"
):
    """Downsample a 2D numpy array to a specified image size

    Args:
        data_x: x-axis values
        data_y: y-axis values
        values: array of values to plot
        image_size: size of the image to output
        plate_size: size of the build plate (meters)
        bottom_left: [X,Y] coordinate (meters) associated with bottom-left of image
        mode: method for downsampling (default "max")
    """
    # Ensure inputs are numpy arrays and of float type
    data_x = np.asarray(data_x, dtype=np.float64)
    data_y = np.asarray(data_y, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)

    # Filter out non-finite values from data_x, data_y, and values
    mask = np.isfinite(data_x) & np.isfinite(data_y) & np.isfinite(values)
    data_x = data_x[mask]
    data_y = data_y[mask]
    values = values[mask]

    # Initialize output image
    image = np.zeros(shape=(image_size, image_size))

    # Scale data to integer image pixel locations (divide by sample_size)
    # and center values on pixel centers (add 0.5)
    sample_size = plate_size / image_size
    scaled_x = (data_x - bottom_left[0]) / sample_size
    scaled_y = (data_y - bottom_left[1]) / sample_size

    # Check for any remaining invalid values before conversion
    valid_mask_x = np.isfinite(scaled_x) & (scaled_x >= 0) & (scaled_x < image_size)
    valid_mask_y = np.isfinite(scaled_y) & (scaled_y >= 0) & (scaled_y < image_size)
    valid_mask = valid_mask_x & valid_mask_y

    i = np.clip(scaled_x[valid_mask].astype(int), 0, image_size - 1)
    j = np.clip(scaled_y[valid_mask].astype(int), 0, image_size - 1)
    values = values[valid_mask]

    # Convert data to 2D using the specified method
    if mode == "max":
        np.maximum.at(image, (i, j), values)
    elif mode == "min":
        np.minimum.at(image, (i, j), values)
    elif mode == "average":
        np.add.at(image, (i, j), values)
        image2 = np.zeros(shape=image.shape)
        np.add.at(image2, (i, j), np.ones(shape=values.shape))
        image = image / (image2 + (image2 == 0))

    return np.rot90(image)
