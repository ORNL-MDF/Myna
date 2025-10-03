#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for an ORNL MDF Peregrine build's file structure"""

from myna.core.db import Database
from myna.core import metadata
from myna.core.utils import downsample_to_image, get_synonymous_key, nested_get
from myna.core.workflow import load_input
import matplotlib.pyplot as plt
import os
import numpy as np
import polars as pl
import warnings


class PeregrineDB(Database):

    synonyms = {
        "laser_power": ["Laser Beam Power (W)", "Power (W)"],
        "laser_spot_size": ["Laser Spot Size (µm)", "Spot Size (µm)", "Spot Size (mm)"],
    }

    def __init__(self):
        Database.__init__(self)
        self.description = "ORNL MDF Peregrine build file structure"
        self.build_segmentation_type = "layer"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the build folder on the Peregrine server
        """
        self.path = path
        self.path_dir = os.path.join(path, "Peregrine")

        # Note: In September 2024, the Peregrine simulation data directory for
        # Myna-related data moved from "Peregrine/simulation" to
        # "Peregrine/simulation/meltpool".
        self.simulation_dir = os.path.join(self.path_dir, "simulation", "meltpool")
        if not os.path.isdir(self.simulation_dir):
            old_simulation_dir = os.path.join(self.path_dir, "simulation")
            if os.path.isdir(old_simulation_dir):
                warnings.warn(
                    'Found metadata in "Peregine/simulation" directory in database.'
                    + "\n\tThis is an outdated directory structure and likely"
                    + " has resulted from working on a stale copy of Peregrine data."
                    + "\n\tThis structure will not be supported in future releases."
                    + "\n\tPlease move relevant simulation metadata to"
                    + " `Peregrine/simulation/meltpool`\n",
                    FutureWarning,
                )
                self.simulation_dir = old_simulation_dir

    def exists(self):
        return (
            os.path.isdir(self.path)
            and os.path.isdir(self.path_dir)
            and os.path.isdir(self.simulation_dir)
        )

    def get_cui_info(self):
        """Get any markings about controlled unclassified information (CUI)"""
        cui_dict = {"flag_sensitive": None, "bannerLine": None, "signatureBlock": None}
        try:
            with np.load("meta.npz") as data:
                cui_dict["flag_sensitive"] = data["flag_sensitive"]
                cui_dict["bannerLine"] = data["bannerLine"]
                cui_dict["signatureBlock"] = data["signatureBlock"]
        except:
            pass
        return cui_dict

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
            datafile = os.path.join(self.simulation_dir, part, "part.npz")
            with np.load(datafile, allow_pickle=True) as data:
                parameter_name = get_synonymous_key(
                    data["parameter_names"], self.synonyms["laser_power"]
                )
                index = list(data["parameter_names"]).index(parameter_name)
                value = float(data["parameter_values"][index])
            return value

        elif metadata_type == metadata.LayerThickness:
            datafile = os.path.join(self.simulation_dir, "buildmeta.npz")
            with np.load(datafile, allow_pickle=True) as data:
                conversion = 1e-3  # millimeters -> meters
                value = float(data["layer_thickness"] * conversion)
            return value

        elif metadata_type == metadata.Material:
            datafile = os.path.join(self.simulation_dir, "buildmeta.npz")
            with np.load(datafile, allow_pickle=True) as data:
                value = str(data["material"])
            return value

        elif metadata_type == metadata.Preheat:
            datafile = os.path.join(self.simulation_dir, "buildmeta.npz")
            # Preheat data is not always stored in Peregrine, as most machines
            # don't actually have a base plate heater
            try:
                with np.load(datafile, allow_pickle=True) as data:
                    index = [
                        ind
                        for ind, x in enumerate(data["metadata_names"])
                        if x == "Target Preheat (°C)"
                    ][0]
                    value = float(data["metadata_values"][index]) + 273.15
            except LookupError:
                warnings.warn("No `Preheat` metadata, assuming room temperature.")
                value = 293.15  # room temperature (20 C)
            return value

        elif metadata_type == metadata.SpotSize:
            datafile = os.path.join(self.simulation_dir, part, "part.npz")
            with np.load(datafile, allow_pickle=True) as data:
                parameter_name = get_synonymous_key(
                    data["parameter_names"], self.synonyms["laser_spot_size"]
                )
                index = list(data["parameter_names"]).index(parameter_name)
                value = float(data["parameter_values"][index])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns and correct accordingly.
            if value > 10:
                value = value * 1e-3

            return value

        elif metadata_type == metadata.STL:
            file_database = os.path.join(self.simulation_dir, part, f"part.stl")
            return file_database

        elif metadata_type == metadata.Scanpath:
            file_database = os.path.join(
                self.simulation_dir, part, f"{self.layer_str(layer)}.txt"
            )
            return file_database

        elif metadata_type == metadata.PartIDMap:
            file_database = os.path.join(
                self.simulation_dir, f"part_id_map_{self.layer_str(layer)}.parquet"
            )
            if not os.path.exists(file_database):
                df = pl.DataFrame(
                    schema={"part_id": str, "x (m)": float, "y (m)": float}
                )
                for p in list(part):
                    file_database_part = os.path.join(
                        self.simulation_dir, p, f"{self.layer_str(layer)}.txt"
                    )
                    df_p = pl.read_csv(file_database_part, separator="\t")
                    df_p = df_p.with_columns(pl.lit(p).alias("part_id"))
                    df_p = df_p.with_columns((pl.col("X(mm)") * 1e-3).alias("x (m)"))
                    df_p = df_p.with_columns((pl.col("Y(mm)") * 1e-3).alias("y (m)"))
                    df_p = df_p.select(["part_id", "x (m)", "y (m)"])
                    df = pl.concat([df, df_p], how="diagonal")
                df.write_parquet(file_database, compression="lz4")
            return file_database

        elif metadata_type == metadata.PrintOrder:
            # TODO: Currently there is not a clear way of how to extract this metadata
            # from a Peregrine database, but it is needed for a project.
            # - For now, assume that the print order equivalent to the sorted part names
            value = []
            part_names = [os.path.basename(d) for d in os.listdir(self.simulation_dir)]
            part_names = [d for d in part_names if d[0] == "P"]
            value = sorted(part_names, key=lambda x: int(x[1:]))
            return value

        else:
            print(f"Error loading: {metadata_type}")
            raise NotImplementedError

    def get_plate_size(self):
        """Load the (x,y) build plate size in meters"""
        with np.load(os.path.join(self.simulation_dir, "buildmeta.npz")) as data:
            value = [x / 1e3 for x in data["actual_size"]]
        return value

    def get_sync_image_size(self):
        """Load the (x,y) image size in pixels"""
        with np.load(os.path.join(self.simulation_dir, "buildmeta.npz")) as data:
            value = data["image_size"]
        return value

    def sync(self, component_type, step_types, output_class, files):
        """Sync result files to the database using Peregrine-style directory
        and file structure.

        Args:
          component_type: (str) name of workflow component app, i.e., Component.component_application
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
        is_build_region_type = "build_region" in step_types
        synced_files = []
        layer_files = {}

        # If build_region type, then return because there is not currently a way to get
        # the `partnumbers` array from a layer in a build_region
        if is_build_region_type:
            return synced_files

        if is_layer_type:
            # Get layers associated with each file
            layers = [
                int(os.path.basename(os.path.dirname(os.path.dirname(f))))
                for f in files
            ]
            unique_layers = sorted(set(layers))
            for layer in unique_layers:
                layer_files[str(layer)] = []
            for f, layer in zip(files, layers):
                layer_files[str(layer)].append(f)

        elif is_region_type:
            # Get middle layer associated with each region
            regions = [
                os.path.basename(os.path.dirname(os.path.dirname(f))) for f in files
            ]
            parts = [
                os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(f))))
                for f in files
            ]
            filebase = os.path.basename(files[0])
            builddir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(files[0])))
            )
            component_name = os.path.basename(os.path.dirname(files[0]))
            unique_regions = sorted(set(regions))
            unique_parts = sorted(set(parts))
            settings = load_input(os.environ["MYNA_INPUT"])
            for region in unique_regions:
                for part in unique_parts:
                    part_dict = nested_get(settings, ["data", "build", "parts"]).get(
                        part
                    )
                    regions_dict = part_dict.get("regions")
                    if regions_dict is not None:
                        region_dict = regions_dict.get(region)
                        if region_dict is not None:
                            layers = region_dict.get("layers")
                            if layers is not None:
                                layers = sorted(layers)
                                index = int(
                                    min(np.ceil(len(layers) / 2), len(layers) - 1)
                                )
                                filename = os.path.join(
                                    builddir, part, region, component_name, filebase
                                )
                                layer_files[str(layers[index])] = [filename]

        # Get build plate size (assume square)
        plate_size = self.get_plate_size()[0]

        # Write data to NPZ file
        for key in layer_files.keys():
            print(f"  - layer: {key}")

            # Get the output fields
            prefix = f"myna_{component_type}_"
            var_names = [
                f"{prefix}{x.name}"
                for x in output_class("").variables
                if x.name not in ["x", "y"]
            ]
            var_units = [
                x.units for x in output_class("").variables if x.name not in ["x", "y"]
            ]

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
                    try:
                        out = output_class(f)
                        (
                            locator,
                            file_values,
                            value_names,
                            _,
                        ) = out.get_values_for_sync(mode="spatial_2d")
                    except (NotImplementedError, KeyError):
                        print(f"- No data to sync for {f}")
                        continue
                    x, y = locator

                    # Get values only from the relevant variable
                    var_index = value_names.index(var_name.replace(prefix, ""))
                    sim_values = file_values[var_index]

                    # Get metadata from file path
                    split_path = f.split(os.path.sep)
                    app = split_path[-2]
                    if is_region_type:
                        region = split_path[-3]
                        part = split_path[-4]
                    else:
                        region = None
                        layer = int(split_path[-3])
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
