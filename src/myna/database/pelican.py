#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for extracting data from MDF Pelican build data"""
import os
import glob
import yaml
from datetime import datetime, timedelta
import zarr
import numpy as np
import polars as pl
from myna.core import metadata
from myna.core.db import Database
from myna.core.utils import nested_get, nested_set


class Pelican(Database):
    """Database of Pelican data for a directed energy deposition build"""

    def __init__(self):
        Database.__init__(self)
        self.description = "MDF Pelican database"
        self.scan_data_dir = None
        self.info_filepath = None
        self.scanpath_export_dir = None
        self.scan_export_dict = None
        self.set_time_range()

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the directory containing Pelican build data
        """
        self.path = path
        self.path_dir = self.path
        self.scan_data_dir = os.path.join(self.path_dir, "simulations")
        self.info_filepath = os.path.join(self.path_dir, "info.yaml")
        self.scanpath_export_dir = os.path.join(self.path_dir, "myna_scanpaths")
        self.scan_export_dict = os.path.join(
            self.scanpath_export_dir, "export_info.yaml"
        )

    def set_time_range(self, start_time=None, end_time=None, origin=None):
        """Sets the start and end time to consider in the database when extracting
        metadata. This may be necessary/desired if the build is very large.

        Args:
            start_time: (float, None) first time to consider in build, in seconds
            end_time: (float, None) last time to consider in build, in seconds
            origin: ([x,y,z,t], None) starting x, y, z, and t values to use, given that
                complete position information may not exist in the time frame specified.
                If None, will crop simulated time frame to the largest completely
                defined subset of times in the stated range, so simulation results may
                not span the entire specified time.
        """
        self.start_time = start_time
        self.end_time = end_time
        self.origin = origin

    def exists(self):
        return os.path.exists(self.path)

    def load(
        self, metadata_type, part=None, layer=None
    ):  # pylint: disable=unused-argument
        """Load and return a metadata value from the database

        Note that layer is never used, because Pelican does not have the layer concept
        """
        with open(self.info_filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # ==============================================================================
        # Data values
        # ==============================================================================
        if metadata_type == metadata.Material:
            return nested_get(data, ["material"])

        if metadata_type == metadata.LayerThickness:
            return nested_get(data, ["layer_thickness"])  # mm

        if metadata_type == metadata.Preheat:
            return nested_get(data, ["preheat"])  # K

        if metadata_type == metadata.PartIDMap:
            return nested_get(data, ["print_order"])

        if metadata_type == metadata.LaserPower:
            return nested_get(data, [part, "laser_power"])  # W

        if metadata_type == metadata.SpotSize:
            return nested_get(data, [part, "spot_size"])  # mm, D4sigma

        # ==============================================================================
        # File paths
        # ==============================================================================
        if metadata_type == metadata.Scanpath:
            return self.get_scan_path(part)

        if metadata_type == metadata.STL:
            return nested_get(data, ["stl"])

        if metadata_type == metadata.PartIDMap:
            return nested_get(data, ["part_id_map"])

        return None

    def get_scan_path(self, part):
        """Extracts the scan path file for the database if needed,
        then returns the scanpath file path

        Args:
            part: (str) part name to extract data for
        """

        # Check if there is a file with info for previous exports, and if previous
        # exports match current start_time and end_time
        matching_file = None
        scan_exports = {}
        part_str = str(part)
        scan_export_name = None
        if os.path.exists(self.scan_export_dict):
            with open(self.scan_export_dict, "r", encoding="utf-8") as f:
                scan_exports = yaml.safe_load(f)
            for key, entry in scan_exports[part_str].items():
                if (
                    entry["start_time"] == self.start_time
                    and entry["end_time"] == self.end_time
                ):
                    matching_file = key

        if matching_file is None:

            # Get name of new scanpath file
            index = len(
                glob.glob(
                    os.path.join(
                        self.scanpath_export_dir,
                        part_str,
                        "scanpath[0-9][0-9][0-9].txt",
                    )
                )
            )
            scan_name = f"scanpath{index:03}.txt"
            scan_dict = {"start_time": self.start_time, "end_time": self.end_time}
            nested_set(scan_exports, [part_str, scan_name], scan_dict)

            # Export scan path data
            scan_export_name = os.path.join(
                self.scanpath_export_dir, part_str, scan_name
            )
            os.makedirs(os.path.dirname(scan_export_name), exist_ok=True)
            df = self.load_pelican_data(datatype="raw")
            df = self.clean_pelican_data(df)
            df_myna = self.convert_dataframe_to_myna_scanpath(df)
            df_myna.write_csv(scan_export_name, separator="\t")

            # Write updated scan export dict
            with open(self.scan_export_dict, "w", encoding="utf-8") as f:
                yaml.dump(scan_exports, f, default_flow_style=None)
        else:
            scan_export_name = os.path.join(self.scan_export_dict, matching_file)

        return scan_export_name

    def initialize_dataframe(
        self, origin=None, epoch=datetime(1970, 1, 1, tzinfo=None)
    ):
        """Loads the raw x, y, z, and time data from the Pelican simulation data directory.

        Args:
            path: (str) path to the Pelican directory
            origin: (None, [x,y,z,time]) start position and time
            datatype: (str) ["raw", "resampled"] type of data to load from Pelican
            epoch: (datetime.datetime instance) datetime object to use as the epoch

        Returns:
            polars.DataFrame instance with the columns:
            - "x (mm)": float, X-coordinate in meters at given time
            - "y (mm)": float, Y-coordinate in meters at given time
            - "z (mm)": float, Z-coordinate in meters at given time
            - "time (s)": float, time in seconds corresponding to the XYZ location
            - "time": pl.Datetime, time since epoch
        """
        # Initialize DataFrame
        schema = {
            "x (mm)": pl.Float64,
            "y (mm)": pl.Float64,
            "z (mm)": pl.Float64,
            "time (s)": pl.Float64,
            "time": pl.Datetime,
        }
        if origin is None:
            df = pl.DataFrame({key: [] for key in schema}, schema=schema)
        else:
            df = pl.DataFrame(
                {
                    "x (mm)": [origin[0]],
                    "y (mm)": [origin[1]],
                    "z (mm)": [origin[2]],
                    "time (s)": [origin[3]],
                    "time": [epoch + timedelta(seconds=origin[3])],
                },
                schema=schema,
            )
        return df

    def load_pelican_data(
        self,
        datatype="raw",
        epoch=datetime(1970, 1, 1, tzinfo=None),
    ):
        """Loads the raw x, y, z, and time data from the Pelican simulation data directory.

        Args:
            datatype: (str) ["raw", "resampled"] type of data to load from Pelican
            epoch: (datetime.datetime instance) datetime object to use as the epoch

        Returns:
            polars.DataFrame instance with the columns defined by `initialize_dataframe()`
        """

        df = self.initialize_dataframe(self.origin, epoch)
        schema = df.schema
        pelican_dims = ["x", "y", "z"]

        # Load raw Pelican data
        for dim in pelican_dims:

            # Get data
            data = zarr.open(f"{self.scan_data_dir}/{dim}", mode="r")
            locs = np.array(data[f"{datatype}/data"])
            times = np.array(data[f"{datatype}/times"])
            times_datetime = pl.Series(times * 1e6).cast(pl.Duration) + epoch  # s -> us
            blanks = pl.Series(
                name="blanks", values=[None] * len(locs), dtype=pl.Float64
            )

            # Construct DataFrame
            dim_key = dim + " (mm)"
            other_keys = set(pelican_dims)
            other_keys.discard(dim)
            other_keys = [k + " (mm)" for k in list(other_keys)]
            df_data = pl.DataFrame(
                {
                    dim_key: locs,
                    other_keys[0]: blanks,
                    other_keys[1]: blanks,
                    "time (s)": times,
                    "time": times_datetime,
                },
                schema=schema,
            )
            df_data = df_data.select(schema)
            df = pl.concat([df, df_data])

        # Ensure only one entry at each time
        other_keys = set(schema)
        other_keys.discard("time")
        df = df.group_by("time").agg([pl.col(col).max() for col in other_keys])
        df = df.select(list(schema)).sort("time")
        return df

    def clean_pelican_data(self, df):
        """Cleans pelican data to ensure that there are no null rows left in the DataFrame

        Args:
            df: (polars.DataFrame) DataFrame containing "x (mm)", "y (mm)", "z (mm)",
                "time (s)" and "time" columns
        """
        # Fill out table by linearly interpolating values and replace NaN with null
        df_clean = df.with_columns(
            [
                (pl.col("x (mm)").interpolate_by("time").replace(np.nan, None)).alias(
                    "x (mm)"
                ),
                (pl.col("y (mm)").interpolate_by("time").replace(np.nan, None)).alias(
                    "y (mm)"
                ),
                (pl.col("z (mm)").interpolate_by("time").replace(np.nan, None)).alias(
                    "z (mm)"
                ),
                (pl.col("time (s)").alias("time (s)")),
                (pl.col("time").alias("time")),
            ]
        )

        # Drop null rows
        df_clean = df_clean.drop_nulls()
        return df_clean

    def convert_dataframe_to_myna_scanpath(self, df, power=1):
        """Converts a polars.DataFrame in the `initialize_dataframe()` schema to a Myna
        scan path.

        Args:
            df: (polars.DataFrame)
            power: (float) Power, in Watts
        """
        myna_schema = {
            "Mode": int,
            "X(mm)": float,
            "Y(mm)": float,
            "Z(mm)": float,
            "Pmod": float,
            "tParam": float,
        }
        df_myna = pl.DataFrame({k: [] for k in myna_schema}, schema=myna_schema)
        df_init = pl.DataFrame(
            {
                "Mode": [1],
                "X(mm)": df[0]["x (mm)"],
                "Y(mm)": df[0]["y (mm)"],
                "Z(mm)": df[0]["z (mm)"],
                "Pmod": [0],
                "tParam": df[0]["time (s)"],
            },
            schema=myna_schema,
        )
        df_myna = pl.concat([df_myna, df_init])
        if isinstance(power, (int, float)):
            xs = df.select("x (mm)")[1:].to_numpy()
            ys = df.select("y (mm)")[1:].to_numpy()
            zs = df.select("z (mm)")[1:].to_numpy()
            velocities = (
                1e-3
                * np.sqrt(
                    np.power(
                        df.select("x (mm)").to_numpy()[1:]
                        - df.select("x (mm)").to_numpy()[:-1],
                        2,
                    )
                    + np.power(
                        df.select("y (mm)").to_numpy()[1:]
                        - df.select("y (mm)").to_numpy()[:-1],
                        2,
                    )
                    + np.power(
                        df.select("z (mm)").to_numpy()[1:]
                        - df.select("z (mm)").to_numpy()[:-1],
                        2,
                    )
                )
                / (
                    df.select("time (s)").to_numpy()[1:]
                    - df.select("time (s)").to_numpy()[:-1]
                )
            )
            df_rasters = pl.DataFrame(
                {
                    "Mode": np.zeros((len(df) - 1)),
                    "X(mm)": xs.flatten(),
                    "Y(mm)": ys.flatten(),
                    "Z(mm)": zs.flatten(),
                    "Pmod": np.ones((len(df) - 1)) * power,
                    "tParam": velocities.flatten(),
                },
                schema=myna_schema,
            )
            df_myna = pl.concat([df_myna, df_rasters])
        else:
            raise ValueError("Only single value is accepted for power.")

        return df_myna
