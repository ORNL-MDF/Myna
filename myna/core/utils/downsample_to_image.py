import numpy as np


def downsample_to_image(data_x, data_y, values, image_size, plate_size, mode="max"):
    """Downsample a 2D numpy array to a specified image size

    Keyword arguments:
    data_x -- x-axis values
    data_y -- y-axis values
    values -- array of values to plot
    image_size -- size of the image to output
    plate_size -- size of the build plate (meters)
    mode -- method for downsampling (default "max")
    """
    # Initialize output image
    image = np.zeros(shape=(image_size, image_size))

    # Scale data to integer image pixel locations (divide by sample_size)
    # and center values on pixel centers (add 0.5)
    sample_size = plate_size / image_size
    i, j = np.array(data_x / sample_size + 0.5, dtype=int), np.array(
        data_y / sample_size + 0.5, dtype=int
    )

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
