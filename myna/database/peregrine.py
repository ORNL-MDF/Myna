"""Database class for an ORNL MDF Peregrine build's file structure"""

from myna.core.db import Database
from myna.core import metadata
from myna.core.utils import downsample_to_image
import matplotlib.pyplot as plt
import os
import numpy as np


class PeregrineDB(Database):
    def __init__(self):
        Database.__init__(self)
        self.description = "ORNL MDF Peregrine build file structure"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the build folder on the Peregrine server
        """
        self.path = os.path.join(path, "Peregrine")
        self.path_dir = self.path

    def exists(self):
        return os.path.isdir(self.path)

    def load(self, metadata_type, part=None, layer=None):
        """Load and return a metadata value from the database

        Implemented metadata loaders:
        - LaserPower
        - LayerThickness
        - Material
        - Preheat
        - SpotSize
        - STL
        - Scanpath
        """

        if metadata_type == metadata.LaserPower:
            datafile = os.path.join(self.path, "simulation", part, "part.npz")
            with np.load(datafile, allow_pickle=True) as data:
                index = [
                    ind
                    for ind, x in enumerate(data["parameter_names"])
                    if x == "Power (W)"
                ][0]
                value = float(data["parameter_values"][index])
            return value

        elif metadata_type == metadata.LayerThickness:
            datafile = os.path.join(self.path, "simulation", "buildmeta.npz")
            with np.load(datafile, allow_pickle=True) as data:
                conversion = 1e-3  # millimeters -> meters
                value = float(data["layer_thickness"] * conversion)
            return value

        elif metadata_type == metadata.Material:
            datafile = os.path.join(self.path, "simulation", "buildmeta.npz")
            with np.load(datafile, allow_pickle=True) as data:
                value = str(data["material"])
            return value

        elif metadata_type == metadata.Preheat:
            datafile = os.path.join(self.path, "simulation", "buildmeta.npz")
            with np.load(datafile, allow_pickle=True) as data:
                index = [
                    ind
                    for ind, x in enumerate(data["metadata_names"])
                    if x == "Target Preheat (°C)"
                ][0]
                value = float(data["metadata_values"][index]) + 273.15
            return value

        elif metadata_type == metadata.SpotSize:
            datafile = os.path.join(self.path, "simulation", part, "part.npz")
            with np.load(datafile, allow_pickle=True) as data:
                index = [
                    ind
                    for ind, x in enumerate(data["parameter_names"])
                    if x == "Spot Size (mm)"
                ][0]
                value = float(data["parameter_values"][index])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns and correct accordingly.
            if value > 10:
                value = value * 1e-3

            return value

        elif metadata_type == metadata.STL:
            file_database = os.path.join(self.path, "simulation", part, f"part.stl")
            return file_database

        elif metadata_type == metadata.Scanpath:
            file_database = os.path.join(
                self.path, "simulation", part, f"{self.layer_str(layer)}.txt"
            )
            return file_database

        else:
            print(f"Error loading: {metadata_type}")
            raise NotImplementedError

    def get_plate_size(self):
        """Load the (x,y) build plate size in meters"""
        with np.load(os.path.join(self.path, "simulation", "buildmeta.npz")) as data:
            value = [x / 1e3 for x in data["actual_size"]]
        return value

    def get_sync_image_size(self):
        """Load the (x,y) image size in pixels"""
        with np.load(os.path.join(self.path, "simulation", "buildmeta.npz")) as data:
            value = data["image_size"]
        return value

    def sync(self, component_type, step_types, output_class, files):
        """Sync result files to the database using Peregrine-style directory
        and file structure.

        Args:
          component_type: (str) name of workflow component interface, i.e., Component.component_interface
          step_types: (list of str) list of workflow component types, i.e., Component.types
          output_class: class object for the output file, e.g., Component.output_requirement
          files: List of files to sync for the passed workflow component

        Returns:
          synced_files: list of files that were synced

        For each layer:
        1. Open the corresponding NPZ file
        2. Save all corresponding data
        3. Close NPZ file
        4. Write thumbnail file
        """
        is_layer_type = "layer" in step_types
        is_region_type = "region" in step_types
        synced_files = []
        if is_layer_type:
            # Get layers associated with each file
            layers = [
                int(os.path.basename(os.path.dirname(os.path.dirname(f))))
                for f in files
            ]
            unique_layers = sorted(set(layers))
            layer_files = {}
            for layer in unique_layers:
                layer_files[str(layer)] = []
            for f, layer in zip(files, layers):
                layer_files[str(layer)].append(f)

            # Get build plate size (assume square)
            plate_size = self.get_plate_size()[0]

            # Write data to NPZ file
            for key in layer_files.keys():
                print(f"  - layer: {key}")

                # Get the output fields
                prefix = f"myna_{component_type}"
                try:
                    var_names, var_units = output_class(f).get_names_for_sync(
                        prefix=prefix
                    )
                except:
                    print("    - Sync not implemented for any files")
                    continue

                # Loop through the output fields
                for var_name, var_unit in zip(var_names, var_units):
                    print(f"    - field: {var_name}")

                    # Make target output_path
                    output_path = os.path.join(self.path_dir, "registered", var_name)
                    if not os.path.exists(output_path):
                        os.makedirs(output_path)

                    # Get file path
                    npz_filepath = f"{self.layer_str(key)}.npz"
                    fullpath = os.path.join(output_path, npz_filepath)

                    # Open NPZ file and get existing data or initialize data
                    if os.path.exists(fullpath):
                        with np.load(fullpath, allow_pickle=True) as data:
                            xcoords = data["coords_x"]
                            ycoords = data["coords_y"]
                            partnumbers = data["part_num"]
                            values = data["values"]
                    else:
                        xcoords = np.array([])
                        ycoords = np.array([])
                        partnumbers = np.array([])
                        values = np.array([])

                    # Loop through all the files for the layer to add data
                    for f in layer_files[key]:
                        out = output_class(f)
                        (
                            x,
                            y,
                            file_values,
                            value_names,
                            _,
                        ) = out.get_values_for_sync(prefix=prefix)

                        # Get values only from the relevant variable
                        var_index = value_names.index(var_name)
                        sim_values = file_values[var_index]

                        # Get metadata from file path
                        split_path = f.split(os.path.sep)
                        interface = split_path[-2]
                        layer = int(split_path[-3])
                        if is_region_type:
                            region = split_path[-4]
                            part = split_path[-5]
                        else:
                            region = None
                            part = split_path[-4]

                        partnumber = int(part.replace("P", ""))

                        # If a there is existing data, then empty any previous
                        # data with same part number and add new data

                        # Mask current part number
                        other_parts_in_layer = partnumbers != partnumber

                        # Get coordinates and values outside the masked region
                        xcoords = xcoords[other_parts_in_layer]
                        ycoords = ycoords[other_parts_in_layer]
                        other_partnumbers = partnumbers[other_parts_in_layer]
                        values = values[other_parts_in_layer]

                        # Add new values to masked region
                        xcoords = np.concatenate([xcoords, x])
                        ycoords = np.concatenate([ycoords, y])
                        partnumbers = np.concatenate(
                            [other_partnumbers, np.ones(x.shape) * partnumber]
                        )
                        values = np.concatenate([values, sim_values])

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
                    output_file = self.make_thumbnail_image(int(key), var_name)
                    print(f"    - output_file: {output_file}")
                    synced_files.append(output_file)

        return synced_files

    def make_thumbnail_image(self, layernumber, var_name="Test"):
        # Get FilePath
        subpath = os.path.join("registered", var_name)
        filepath = f"{self.layer_str(layernumber)}.npz"
        fullpath = os.path.join(self.path_dir, subpath, filepath)

        # Get Build and Image Size (assume square)
        plate_size = self.get_plate_size()[0]
        image_size = self.get_sync_image_size()[0]

        # Load Data
        with np.load(fullpath, allow_pickle=True) as data:
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
            bottom_left=[0, 0],
            mode="average",
        )
        filepath = f"{self.layer_str(layernumber)}.png"
        fullpath = os.path.join(self.path_dir, subpath, filepath)
        plt.imsave(fullpath, image, cmap="gray")

        return fullpath

    def layer_str(self, layernumber):
        return f"{int(layernumber):07}"
