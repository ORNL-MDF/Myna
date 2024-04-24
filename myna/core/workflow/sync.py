import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt
import argparse
import myna.core.utils
import myna.core.components
import myna.database
from myna.core.workflow.load_input import load_input


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


def upload_results(
    datatype,
    partnumber,
    layernumber,
    x,
    y,
    sim_values,
    var_name="Test",
    var_unit="Test",
):
    """Uploads information from result file to Peregrine database"""

    # Make target output_path
    output_path = os.path.join(datatype.path_dir, "registered", var_name)
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    # Get file path
    filepath = f"{layernumber:07}.npz"
    fullpath = os.path.join(output_path, filepath)

    # Get build plate size (assume square)
    plate_size = datatype.get_plate_size()[0]

    # If a corresponding .npz file exists,
    # then empty any previous data with same part number and add new
    if os.path.exists(fullpath):
        data = np.load(fullpath, allow_pickle=True)

        # Mask current part number
        other_parts_in_layer = data["part_num"] != partnumber

        # Get coordinates and values outside the masked region
        xcoords = data["coords_x"][other_parts_in_layer]
        ycoords = data["coords_y"][other_parts_in_layer]
        other_partnumbers = data["part_num"][other_parts_in_layer]
        values = data["values"][other_parts_in_layer]

        # Add new values to masked region
        xcoords = np.concatenate([xcoords, x])
        ycoords = np.concatenate([ycoords, y])
        partnumbers = np.concatenate([other_partnumbers, np.ones(x.shape) * partnumber])
        values = np.concatenate([values, sim_values])

    # If the file does not exist, then save data
    else:
        xcoords = x
        ycoords = y
        partnumbers = np.ones(xcoords.shape) * partnumber
        values = sim_values

    # Calculate "m" and "b" for Peregrine color map
    y1 = np.min(values)
    y2 = np.max(values)
    x1 = np.iinfo(np.uint8).min
    x2 = np.iinfo(np.uint8).max
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1

    # Save using the Peregrine expected field
    np.savez_compressed(
        fullpath,
        dtype="points",
        units=f"{var_name} ({var_unit})",
        shape_x=plate_size,
        shape_y=plate_size,
        part_num=partnumbers,
        coords_x=xcoords,
        coords_y=ycoords,
        values=values,
        m=m,
        b=b,
    )

    # Make image of data (required for Peregrine)
    fullpath = make_image(datatype, layernumber, var_name)

    return fullpath


def make_image(datatype, layernumber, var_name="Test"):
    # Get FilePath
    subpath = os.path.join("registered", var_name)
    filepath = f"{layernumber:07}.npz"
    fullpath = os.path.join(datatype.path_dir, subpath, filepath)

    # Get Build and Image Size (assume square)
    plate_size = datatype.get_plate_size()[0]
    image_size = datatype.get_sync_image_size()[0]

    # Load Data
    data = np.load(fullpath, allow_pickle=True)
    xcoords = data["coords_x"]
    ycoords = data["coords_y"]
    values = data["values"]

    # Make Image
    image = downsample_to_image(
        data_x=xcoords,
        data_y=ycoords,
        values=values,
        image_size=image_size,
        plate_size=plate_size,
        mode="average",
    )
    filepath = f"{layernumber:07}.png"
    fullpath = os.path.join(datatype.path_dir, subpath, filepath)
    plt.imsave(fullpath, image, cmap="gray")

    return fullpath


def main(argv=None):
    """Main function for running myna_sync from the command line

    Args:
        argv : list of command line arguments, by default None
    """

    # Set up argparse
    parser = argparse.ArgumentParser(
        description="Launch myna for " + "specified input file"
    )
    parser.add_argument(
        "--input",
        default="input.yaml",
        type=str,
        help='(str, default="input.yaml") path to the desired input file to run',
    )
    parser.add_argument(
        "--step",
        type=str,
        help="(str) step or steps to run from the given input file."
        + ' For one step use "--step step_name" and'
        + ' for multiple steps use "--step [step_name_0,step_name_1]"',
    )

    # Parse cmd arguments
    args = parser.parse_args(argv)
    input_file = args.input
    steps_to_sync = myna.core.utils.str_to_list(args.step)

    # Set environmental variable for input file location
    os.environ["MYNA_SYNC_INPUT"] = os.path.abspath(input_file)

    # Load the initial input file to get the steps
    initial_settings = load_input(input_file)

    # Run through each step
    for index, step in enumerate(initial_settings["steps"]):
        # Load the input file at each step in case one the previous step has updated the inputs
        settings = load_input(input_file)

        # Get the step name and class
        step_name = [x for x in step.keys()][0]
        component_class_name = step[step_name]["class"]
        component_interface_name = step[step_name]["interface"]
        step_obj = myna.core.components.return_step_class(component_class_name)
        step_obj.name = step_name
        step_obj.component_class = component_class_name
        step_obj.component_interface = component_interface_name

        # Set environmental variable for the step name
        if index != 0:
            os.environ["MYNA_LAST_STEP_NAME"] = os.environ["MYNA_STEP_NAME"]
            os.environ["MYNA_LAST_STEP_CLASS"] = os.environ["MYNA_STEP_CLASS"]
        else:
            os.environ["MYNA_LAST_STEP_NAME"] = ""
            os.environ["MYNA_LAST_STEP_CLASS"] = ""
        os.environ["MYNA_STEP_NAME"] = step_name
        os.environ["MYNA_STEP_CLASS"] = component_class_name
        os.environ["MYNA_STEP_INDEX"] = str(index)

        # Apply the settings and execute the component, as needed
        sync_step = True
        if steps_to_sync is not None:
            if step_name not in steps_to_sync:
                print(
                    f"Skipping step {step_name}: Step is not in"
                    + " the specified steps to run."
                )
                sync_step = False
        if sync_step:
            step_obj.apply_settings(step[step_name], settings["data"])
            step_obj.sync_output_files()
