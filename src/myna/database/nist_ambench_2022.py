#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for a directory with NIST AM-Bench 2022 build data"""

from myna.core.db import Database
from myna.core import metadata
from myna.core.utils import downsample_to_image, nested_get
from myna.core.workflow import load_input
import matplotlib.pyplot as plt
import numpy as np
import os
import polars as pl
import h5py
import stl


class AMBench2022(Database):
    """NIST AM-Bench data structure

    Specify a directory as the path to the database. Files can be downloaded from
    https://doi.org/10.18434/mds2-2607.

    In order to enable simulation of all parts, the directory must contain the following:

    - AMB2022-01-AMMT-XYPT_v1.h5 (https://data.nist.gov/od/ds/ark:/88434/mds2-2607/Scan_Strategy/AMB2022-01-AMMT-XYPT_v1.h5, 4.97 GB)
    - AMB2022-01-AMMT-PartCAD.STL (https://data.nist.gov/od/ds/ark:/88434/mds2-2607/CAD_Geometry/AMB2022-01-AMMT-PartCAD.STL, 21.9 kB)
    - AMB2022-01-AMMT-RecoaterGuideCAD.STL (https://data.nist.gov/od/ds/ark:/88434/mds2-2607/CAD_Geometry/AMB2022-01-AMMT-RecoaterGuideCAD.STL, 18.7 kB)
    """

    def __init__(self):
        Database.__init__(self)
        self.description = "NIST AM-Bench 2022 build file structure"
        self.build_segmentation_type = "layer"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the folder containing the downloaded AM-Bench data
        """
        self.path = path
        self.path_dir = path
        self.simulation_dir = os.path.join(self.path, "simulation", "meltpool")

    def exists(self):
        return os.path.exists(self.path)

    def load(self, metadata_type, part=None, layer=None):
        """Load and return a metadata value from the database

        Implemented metadata loaders:
        - Scanpath
        - Material
        - LaserPower
        - SpotSize
        """

        if metadata_type == metadata.Scanpath:
            # Extract scan path data to file if it doesn't already exist
            file_database = self.create_scanfile(part, layer)
            return file_database

        elif metadata_type == metadata.Material:
            return "SS316L"

        elif metadata_type == metadata.LaserPower:
            return 285.0  # W

        elif metadata_type == metadata.SpotSize:
            return 0.077  # mm, D4sigma

        elif metadata_type == metadata.LayerThickness:
            return 0.04  # mm

        elif metadata_type == metadata.Preheat:
            return 298  # K

        elif metadata_type == metadata.STL:
            file_database = os.path.join(self.simulation_dir, part, "part.stl")
            if not os.path.exists(file_database):
                part_bounds = self.get_part_bounds(part)
                if part[0] == "P":
                    part_base_stl = os.path.join(
                        self.path, "AMB2022-01-AMMT-PartCAD.STL"
                    )
                    part_mesh = stl.mesh.Mesh.from_file(part_base_stl)
                    # Origin at (0,0) so translate to bottom left of the part bounds
                    part_mesh.x += part_bounds[0]
                    part_mesh.y += part_bounds[2]
                elif part[0] == "G":
                    part_base_stl = os.path.join(
                        self.path, "AMB2022-01-AMMT-RecoaterGuideCAD.STL"
                    )
                    part_mesh = stl.mesh.Mesh.from_file(part_base_stl)
                    # The "RecoaterGuide" STL needs to be rotated before it is translated
                    part_mesh.rotate([1, 0, 0], np.radians(90))
                    part_mesh.z *= -1
                    # Origin at (0,0) so translate to bottom left of the part bounds
                    part_mesh.x += part_bounds[0]
                    part_mesh.y += part_bounds[2]
                part_mesh.save(file_database)
            return file_database

    def create_scanfile(self, part, layer):
        """Create a scanpath file from the HDF5 archive

        Args:
          part: name of the part
          layer: layer number

        Returns:
          file_database: path to the exported file
        """

        scan_timestep = 1e-5  # s

        scan_path_data = os.path.join(self.path, "AMB2022-01-AMMT-XYPT_v1.h5")
        with h5py.File(scan_path_data, "r") as data:
            df = pl.DataFrame(
                {
                    "X": pl.Series(data[f"XYPT/{layer}/X"][0, :], dtype=pl.Float64),
                    "Y": pl.Series(data[f"XYPT/{layer}/Y"][0, :], dtype=pl.Float64),
                    "P": pl.Series(data[f"XYPT/{layer}/P"][0, :], dtype=pl.Float64),
                }
            )

            # Set output file name and ensure directory path exists
            file_database = os.path.join(
                self.simulation_dir, part, f"{self.layer_str(layer)}.txt"
            )
            os.makedirs(os.path.dirname(file_database), exist_ok=True)

            # Only create scan files if files don't already exist
            if not os.path.exists(file_database):
                # For Myna default format, Pmod should be a multiple of the
                # nominal power for the part
                power = 1

                # Assign elapsed time to each row
                entries = df.select(pl.count("X")).item()
                total_time = (entries - 1) * scan_timestep
                times = np.arange(
                    start=0, stop=total_time + scan_timestep, step=scan_timestep
                )
                times = times[:entries]
                df = df.with_columns(pl.Series(name="Time(s)", values=times))

                # Remove rows where power is zero
                df = df.filter(pl.col("P") == 0)

                # Calculate the time since the previous row (dt_last) and to the next row (dt_next)
                active_times = df.get_column("Time(s)").to_numpy()
                dt_last = active_times[1:] - active_times[:-1]
                dt_last = np.insert(dt_last, 0, 0)
                dt_next = active_times[1:] - active_times[:-1]
                dt_next = np.append(dt_next, 0)
                df = df.with_columns(pl.Series(name="dt_last", values=dt_last))
                df = df.with_columns(pl.Series(name="dt_next", values=dt_next))

                # Drop rows that have both dt_last and dt_next equal to scan_timestep
                abs_tol = 1e-7
                df = df.filter(
                    ((pl.col("dt_last") - scan_timestep).abs() > abs_tol)
                    | ((pl.col("dt_next") - scan_timestep).abs() > abs_tol)
                )

                # Add last x and y locations to each row
                xs = df.get_column("X").to_numpy()
                x_last = xs[:-1]
                x_last = np.insert(x_last, 0, 0)
                df = df.with_columns(pl.Series(name="X_last", values=x_last))
                ys = df.get_column("Y").to_numpy()
                y_last = ys[:-1]
                y_last = np.insert(y_last, 0, 0)
                df = df.with_columns(pl.Series(name="Y_last", values=y_last))
                df = df.with_columns(
                    (
                        (
                            (pl.col("X") - pl.col("X_last")).pow(2)
                            + (pl.col("Y") - pl.col("Y_last")).pow(2)
                        ).sqrt()
                    ).alias("dist_to_last")
                )

                # Filter by location
                bounds = self.get_part_bounds(part)
                df = df.filter((pl.col("X") >= bounds[0]) & (pl.col("X") <= bounds[1]))
                df = df.filter((pl.col("Y") >= bounds[2]) & (pl.col("Y") <= bounds[3]))

                # Set up output dictionary
                def make_polars_scan_df(mode=[], x=[], y=[], z=[], pmod=[], t=[]):
                    df = pl.DataFrame(
                        {
                            "Mode": pl.Series(mode, dtype=pl.Int8),
                            "X(mm)": pl.Series(x, dtype=pl.Float64),
                            "Y(mm)": pl.Series(y, dtype=pl.Float64),
                            "Z(mm)": pl.Series(z, dtype=pl.Float64),
                            "Pmod": pl.Series(pmod, dtype=pl.Float64),
                            "tParam": pl.Series(t, dtype=pl.Float64),
                        }
                    )
                    return df

                df_scan = make_polars_scan_df()

                # Iterate through rows sequentially to generate scan path
                time_last_row = None
                for index, row in enumerate(df.iter_rows(named=True)):
                    # If first row in XYPT file, go to point
                    if time_last_row == None:
                        df_row = make_polars_scan_df(
                            [1], [row["X"]], [row["Y"]], [0], [0], [0]
                        )

                    # If the next time is farther away than the scan_timestep, go to start point
                    elif np.abs(row["dt_next"] - scan_timestep) > abs_tol:
                        df_row = make_polars_scan_df(
                            [1], [row["X"]], [row["Y"]], [0], [0], [row["dt_last"]]
                        )

                    # If the last time was longer ago than the scan_timestep, go raster to point
                    elif np.abs(row["dt_last"] - scan_timestep) > abs_tol:
                        scan_speed = (
                            row["dist_to_last"]
                            * 1e-3
                            / (row["Time(s)"] - time_last_row)
                        )
                        df_row = make_polars_scan_df(
                            [0], [row["X"]], [row["Y"]], [0], [power], [scan_speed]
                        )

                    df_scan = df_scan.vstack(df_row)
                    time_last_row = row["Time(s)"]

                # Export to .txt file with tab-separated values
                df_scan.write_csv(file_database, separator="\t")

        return file_database

    def get_plate_size(self):
        """Load the (x,y) build plate size in meters"""
        return np.array([0.1, 0.1])

    def get_sync_image_size(self):
        """Load the (x,y) image size in pixels"""
        return np.array([2000, 2000])

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
        synced_files = []
        layer_files = {}
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
            prefix = f"myna_{component_type}"
            var_names = [
                f"{prefix}_{x.name}"
                for x in output_class.variables
                if x.name not in ["x", "y"]
            ]
            var_units = [
                x.units for x in output_class.variables if x.name not in ["x", "y"]
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
                    var_index = value_names.index(var_name)
                    sim_values = file_values[var_index]

                    # Get metadata from file path
                    split_path = f.split(os.path.sep)
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
            bottom_left=[-50e-3, -50e-3],
            mode="average",
        )
        filepath = f"{self.layer_str(layernumber)}.png"
        fullpath = os.path.join(self.path_dir, subpath, filepath)
        plt.imsave(fullpath, image, cmap="gray")

        return fullpath

    def layer_str(self, layernumber):
        return f"{int(layernumber):07}"

    def get_part_bounds(self, part):
        """Defines the part (inclusive) bounding box in XY coordinates

        AM-Bench doesn't provide a part ID map, so data from the provided
        plaintext descriptions is encoded here.

        Args:
          part: part name string (options: P1, P2, P3, P4, G1, G2)

        Returns
          [xmin, xmax, ymin, ymax]: corners of the rectangular bounding box of the part,
            in millimeters
        """

        def part_name_format(part_name):
            """Define format for part name lookup"""
            return part_name.upper().strip()

        # Look up bounding box based on part name
        if part_name_format(part) == "G1":
            xmin, xmax, ymin, ymax = [-45.01, 45.2, 42.560, 47.497]
        elif part_name_format(part) == "G2":
            xmin, xmax, ymin, ymax = [-45.01, 45.2, -47.440, -42.505]
        elif part_name_format(part) == "P1":
            xmin, xmax, ymin, ymax = [-34.51, 40.615, 28.23, 33.26]
        elif part_name_format(part) == "P2":
            xmin, xmax, ymin, ymax = [-36.51, 38.615, 7.73, 12.76]
        elif part_name_format(part) == "P3":
            xmin, xmax, ymin, ymax = [-38.51, 36.615, -12.77, -7.7]
        elif part_name_format(part) == "P4":
            xmin, xmax, ymin, ymax = [-40.51, 34.615, -33.27, -28.2]

        return [xmin, xmax, ymin, ymax]
