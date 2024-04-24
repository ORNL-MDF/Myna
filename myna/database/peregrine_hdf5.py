"""Database class for an ORNL MDF Peregrine build's file structure
that corresponds to the PEregrine 2023-10 dataset"""

from myna.core.db import Database
from myna.core import metadata
import os
import numpy as np
import h5py
import pandas as pd


class PeregrineHDF5(Database):
    """ORNL MDF Peregrine HDF5 archive structure

    Args:
      version: (default = "v2023_10") version for the HDF5 loader to use. The version
               associated with the public dataset (https://doi.org/10.13139/ORNLNCCS/2008021)
               is set as the default assumed behavior for the data loader.
    """

    def __init__(self, version="v2023_10"):

        Database.__init__(self)
        self.description = "ORNL MDF Peregrine HDF5 archive structure"
        self.version = version

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the HDF5 File
        """
        self.path = path
        self.path_dir = os.path.dirname(path)

    def exists(self):
        return os.path.exists(self.path)

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
            pid = int(str(part).split("P")[-1])  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:
                value = float(data["parts/process_parameters/power"][pid])
            return value

        elif metadata_type == metadata.LayerThickness:
            conversion = 1e-3  # millimeters -> meters
            with h5py.File(self.path, "r") as data:
                value = float(data.attrs["material/layer_thickness"] * conversion)
            return value

        elif metadata_type == metadata.Material:
            with h5py.File(self.path, "r") as data:
                value = str(data.attrs["material/composition"])
            return value

        elif metadata_type == metadata.Preheat:
            with h5py.File(self.path, "r") as data:
                value = float(data["temporal/bottom_chamber_temperature"][0]) + 273.15
            return value

        elif metadata_type == metadata.SpotSize:
            pid = int(str(part).split("P")[-1])  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:
                value = float(data["parts/process_parameters/spot_size"][pid])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns (not millimeters) and correct accordingly.
            if value > 10:
                value = value * 1e-3

            return value

        elif metadata_type == metadata.Scanpath:
            # Extract scan path data to file if it doesn't already exist
            file_database = self.create_scanfile(part, layer)
            return file_database

        else:
            print(f"Error loading: {metadata_type}")
            raise NotImplementedError

    def get_plate_size(self):
        """Load the (x,y) build plate size in meters"""
        with h5py.File(self.path, "r") as data:
            x_dim = data.attrs["printer/x_real_dimension"] / 1e3
            y_dim = data.attrs["printer/y_real_dimension"] / 1e3
            return [x_dim, y_dim]

    def get_sync_image_size(self):
        """Load the (x,y) image size in pixels"""
        with h5py.File(self.path, "r") as data:
            return data["slices/part_ids"].shape[1:]

    def create_scanfile(self, part, layer):
        """Create a scanpath file from the HDF5 archive

        Args:
          part: name of the part
          layer: layer number
        """
        # Set output file name
        basedir = os.path.dirname(self.path)
        file_database = os.path.join(
            basedir, "simulation", str(part), f"{int(layer):07d}.txt"
        )

        # Ensure directory path exists
        os.makedirs(os.path.dirname(file_database), exist_ok=True)

        # Only create scan files if files don't already exist
        if not os.path.exists(file_database):
            pid = int(str(part).split("P")[-1])  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:

                # Get Part ID and scan path information
                part_ids = data["slices/part_ids"]
                scan_path = data[f"scans/{layer}"]
                df_scan = pd.DataFrame(
                    {
                        "xs": scan_path[:, 0],
                        "xe": scan_path[:, 1],
                        "ys": scan_path[:, 2],
                        "ye": scan_path[:, 3],
                        "t": scan_path[:, 4],
                    }
                )

                # Define conversion for pixel -> spatial coordinates
                x_dim = data.attrs["printer/x_real_dimension"]
                y_dim = data.attrs["printer/y_real_dimension"]
                ix = 1
                iy = 0
                dx = x_dim / part_ids[int(layer)].shape[ix]
                dy = y_dim / part_ids[int(layer)].shape[iy]

                # Get bounds in pixel indices
                inds = np.argwhere(part_ids[int(layer)] == pid)
                min_x = np.min(inds[:, ix])
                min_y = np.min(inds[:, iy])
                max_x = np.max(inds[:, ix]) + 1
                max_y = np.max(inds[:, iy]) + 1

                # Convert bounds to millimeters
                pad = 1  # px
                min_x = 0.5 * dx + dx * (min_x - pad)
                min_y = 0.5 * dy + dy * (min_y - pad)
                max_x = 0.5 * dx + dx * (max_x + pad)
                max_y = 0.5 * dy + dy * (max_y + pad)

                # Copy scan path dataframe and invert the y-axis to match part_id map
                df_scan["ys"] = y_dim - df_scan["ys"]
                df_scan["ye"] = y_dim - df_scan["ye"]

                # Filter scan path to only include current part
                df_scan = df_scan[df_scan["xs"] > min_x]
                df_scan = df_scan[df_scan["ys"] > min_y]
                df_scan = df_scan[df_scan["xs"] < max_x]
                df_scan = df_scan[df_scan["ys"] < max_y]
                df_scan = df_scan[df_scan["xe"] > min_x]
                df_scan = df_scan[df_scan["ye"] > min_y]
                df_scan = df_scan[df_scan["xe"] < max_x]
                df_scan = df_scan[df_scan["ye"] < max_y]

                # Export scan path
                df_converted = pd.DataFrame(
                    {
                        "Mode": [],
                        "X(mm)": [],
                        "Y(mm)": [],
                        "Z(mm)": [],
                        "Pmod": [],
                        "tParam": [],
                    }
                )
                scan_speed = (
                    data["parts/process_parameters/velocity"][pid] / 1e3
                )  # mm/s -> m/s
                if len(df_scan) > 0:
                    for _, row in df_scan.iterrows():
                        z = data.attrs["material/layer_thickness"] * float(layer)
                        df_row_move = pd.DataFrame(
                            {
                                "Mode": [1],
                                "X(mm)": [row["xs"]],
                                "Y(mm)": [row["ys"]],
                                "Z(mm)": [z],
                                "Pmod": [0],
                                "tParam": [0],
                            }
                        )
                        df_row_scan = pd.DataFrame(
                            {
                                "Mode": [0],
                                "X(mm)": [row["xe"]],
                                "Y(mm)": [row["ye"]],
                                "Z(mm)": [z],
                                "Pmod": [1],
                                "tParam": [scan_speed],
                            }
                        )
                        if len(df_converted) == 0:
                            df_converted = pd.concat([df_row_move, df_row_scan])
                        else:
                            df_converted = pd.concat(
                                [df_converted, df_row_move, df_row_scan]
                            )
                df_converted.to_csv(file_database, sep="\t", index=False)

        return file_database
