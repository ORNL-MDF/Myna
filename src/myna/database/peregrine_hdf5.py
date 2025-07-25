#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for an ORNL MDF Peregrine build's file structure
that corresponds to the PEregrine 2023-10 dataset"""

import os
import warnings
import h5py
import numpy as np
import pandas as pd
from myna.core import metadata
from myna.database.peregrine import PeregrineDB
from myna.core.utils import get_synonymous_key


class PeregrineHDF5(PeregrineDB):
    """ORNL MDF Peregrine HDF5 archive structure

    Args:
      version: (default = "v2023_10") version for the HDF5 loader to use. The version
               associated with the public dataset (https://doi.org/10.13139/ORNLNCCS/2008021)
               is set as the default assumed behavior for the data loader.
    """

    synonyms = {
        "laser_power": [
            "parts/process_parameters/laser_power",
            "parts/process_parameters/power",
            "parts/process_parameters/bulk_laser_power",
        ],
        "laser_spot_size": [
            "parts/process_parameters/laser_spot_size",
            "parts/process_parameters/spot_size",
            "parts/process_parameters/bulk_laser_spot_size",
        ],
        "laser_scan_speed": [
            "parts/process_parameters/laser_beam_speed",
            "parts/process_parameters/scan_speed",
            "parts/process_parameters/speed",
            "parts/process_parameters/velocity",
            "parts/process_parameters/bulk_laser_beam_speed",
        ],
        "material_name": [
            "material/composition",
            "material/feedstock_0/type",
        ],
    }

    def __init__(self, version="v2023_10"):

        super().__init__()
        self.description = "ORNL MDF Peregrine HDF5 archive structure"
        self.version = version
        self.build_segmentation_type = "layer"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the HDF5 File
        """
        self.path = os.path.abspath(path)
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
            pid = int(
                str(part).split("P", maxsplit=1)[-1]
            )  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:
                name = get_synonymous_key(data, self.synonyms["laser_power"])
                value = float(data[name][pid])
            return value

        if metadata_type == metadata.LayerThickness:
            conversion = 1e-3  # millimeters -> meters
            with h5py.File(self.path, "r") as data:
                value = float(data.attrs["material/layer_thickness"] * conversion)
            return value

        if metadata_type == metadata.Material:
            with h5py.File(self.path, "r") as data:
                name = get_synonymous_key(data.attrs, self.synonyms["material_name"])
                value = str(data.attrs[name])
            return value

        if metadata_type == metadata.Preheat:
            with h5py.File(self.path, "r") as data:
                # Preheat data is not always stored in Peregrine, as most machines
                # don't actually have a base plate heater
                try:
                    value = (
                        float(data["temporal/bottom_chamber_temperature"][0]) + 273.15
                    )
                except LookupError:
                    warnings.warn("No `Preheat` metadata, assuming room temperature.")
                    value = 293.15  # room temperature (20 C)
            return value

        if metadata_type == metadata.SpotSize:
            pid = int(
                str(part).split("P", maxsplit=1)[-1]
            )  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:
                name = get_synonymous_key(data, self.synonyms["laser_spot_size"])
                value = float(data[name][pid])

            # NOTE: Correct for bug in Peregrine that saved spot size as microns
            # in some files. Assume that if the spot size is greater than 10
            # that it is stored in microns (not millimeters) and correct accordingly.
            if value > 10:
                value = value * 1e-3
                warn_msg = (
                    f"Large spot size detected ({value} mm),"
                    + f" assuming conversion um to mm (--> {value*1e-3} mm)"
                )
                warnings.warn(warn_msg)

            return value

        if metadata_type == metadata.Scanpath:
            # Extract scan path data to file if it doesn't already exist
            file_database = self.create_scanfile(part, layer)
            return file_database

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
            part_ids = data["slices/part_ids"]
            if isinstance(part_ids, h5py.Dataset):
                return part_ids.shape[1:]
            raise TypeError(f"Expected a dataset but got {type(part_ids)}")

    def create_scanfile(self, part, layer):
        """Create a scanpath file from the HDF5 archive

        Args:
          part: name of the part
          layer: layer number
        """
        # Set output file name
        basedir = os.path.dirname(self.path)
        file_database = os.path.join(
            basedir, "simulation", str(part), f"{self.layer_str(layer)}.txt"
        )

        # Ensure directory path exists
        os.makedirs(os.path.dirname(file_database), exist_ok=True)

        # Only create scan files if files don't already exist
        if not os.path.exists(file_database):
            pid = int(
                str(part).split("P", maxsplit=1)[-1]
            )  # remove "P" prefix from part name
            with h5py.File(self.path, "r") as data:

                # Get Part ID and scan path information
                # Older versions of Peregrine HDF5 files just have "scans/{layer}",
                # but newer versions of the files have two formats of the scan data:
                # - "scans/{layer} line" (Peregrine "raster" and "contour" lines)
                # - "scans/{layer} point" (xyzt point representation)
                part_ids = data["slices/part_ids"][int(layer)]
                part_ids_shape = None
                if not isinstance(part_ids, h5py.Dataset):
                    part_ids_shape = part_ids.shape  # pylint: disable=no-member
                else:
                    raise TypeError(f"Expected a dataset but got {type(part_ids)}")
                try:
                    scan_path = data[f"scans/{layer} line"]
                except KeyError:
                    scan_path = data[f"scans/{layer}"]
                df_scan = pd.DataFrame(
                    {
                        "xs": scan_path[:, 0],
                        "xe": scan_path[:, 1],
                        "ys": scan_path[:, 2],
                        "ye": scan_path[:, 3],
                        "time_end": scan_path[:, 4],
                    }
                )

                # Define conversion for pixel -> spatial coordinates
                x_dim = data.attrs["printer/x_real_dimension"]
                y_dim = data.attrs["printer/y_real_dimension"]
                ix = 1
                iy = 0
                dx = x_dim / part_ids_shape[ix]
                dy = y_dim / part_ids_shape[iy]

                # Get bounds in pixel indices
                inds = np.argwhere(part_ids == pid)
                min_x = np.min(inds[:, ix])
                min_y = np.min(inds[:, iy])
                max_x = np.max(inds[:, ix]) + 1
                max_y = np.max(inds[:, iy]) + 1

                # Convert bounds to millimeters
                pad = 3  # px
                min_x = dx * (min_x - pad - 0.5)
                min_y = dy * (min_y - pad - 0.5)
                max_x = dx * (max_x + pad + 0.5)
                max_y = dy * (max_y + pad + 0.5)

                # Invert the y-axis to match part_id map
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

                # Undo the inversion of the y-axis to return to original coordinates
                df_scan["ys"] = y_dim - df_scan["ys"]
                df_scan["ye"] = y_dim - df_scan["ye"]

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

                # Find scan speed, which can have variable node names depending
                # on the build
                name = get_synonymous_key(data, self.synonyms["laser_scan_speed"])
                # mm/s -> m/s
                scan_speed = float(data[name][pid]) / 1e3

                if len(df_scan) > 0:
                    time_end_last = 0.0
                    for row_index, row in df_scan.iterrows():
                        duration = np.power(
                            np.power(row["xe"] - row["xs"], 2)
                            + np.power(row["ye"] - row["ys"], 2),
                            0.5,
                        ) / (scan_speed * 1e3)
                        # assume scan path starts from 0.0 elapsed time
                        if row_index == 0:
                            time_end_last = row["time_end"] - duration
                        delay = max(row["time_end"] - duration - time_end_last, 0)
                        z = data.attrs["material/layer_thickness"] * float(layer)
                        df_row_move = pd.DataFrame(
                            {
                                "Mode": [1],
                                "X(mm)": [row["xs"]],
                                "Y(mm)": [row["ys"]],
                                "Z(mm)": [z],
                                "Pmod": [0],
                                "tParam": [delay],
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
                        time_end_last = row["time_end"]
                        if len(df_converted) == 0:
                            df_converted = pd.concat([df_row_move, df_row_scan])
                        else:
                            df_converted = pd.concat(
                                [df_converted, df_row_move, df_row_scan]
                            )
                df_converted.to_csv(file_database, sep="\t", index=False)

        return file_database
