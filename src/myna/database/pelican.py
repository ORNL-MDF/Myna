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
from datetime import datetime, timedelta
import yaml
import zarr
import numpy as np
import polars as pl
from polars.datatypes import Float64
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
        self.sync_timeseries_dir = None
        self.build_segmentation_type = "time"

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the directory containing Pelican build data
        """
        self.path = path
        self.path_dir = self.path
        self.scan_data_dir = os.path.join(self.path_dir, "simulations")
        self.info_filepath = os.path.join(self.scan_data_dir, "settings.yaml")
        self.scanpath_export_dir = os.path.join(self.path_dir, "myna_scanpaths")
        self.scan_export_dict = os.path.join(
            self.scanpath_export_dir, "export_info.yaml"
        )
        self.sync_timeseries_dir = os.path.join(self.path_dir, "registered_timeseries")

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
            return nested_get(data, ["layer thickness"])  # mm

        if metadata_type == metadata.Preheat:
            return nested_get(data, ["preheat"])  # K

        if metadata_type == metadata.PartIDMap:
            return nested_get(data, ["print order"])

        if metadata_type == metadata.LaserPower:
            return nested_get(data, [part, "laser_power"])  # W

        if metadata_type == metadata.SpotSize:
            return nested_get(data, [part, "spot_size"])  # mm, D4sigma

        # ==============================================================================
        # File paths
        # ==============================================================================
        if metadata_type == metadata.Scanpath:
            return self.get_scan_path(part, layer)

        if metadata_type == metadata.STL:
            return nested_get(data, [part, "stl"])

        return None

    def get_segment_details(self, part, layer):
        """Gets the start and end time and starting details for the given "layer"
        in the part. This is a translation layer between the time-segment
        nature of the Pelican database and the layer structure of
        the myna.core.workflow.config functionality.

        Args:
            part: (str) part name to extract data for
            layer: (str) "layer" corresponding to the time_segment for the part in
                the Myna input file
        """
        input_file = os.environ["MYNA_INPUT"]
        with open(input_file, "r", encoding="utf-8") as f:
            input_dict = yaml.safe_load(f)
        segment = nested_get(
            input_dict, ["data", "build", "parts", part, "time_segments"]
        )[int(layer)]
        times = [float(time) for time in segment.split("-")]
        starting_points = {
            key: x[int(layer)]
            for key, x in nested_get(
                input_dict, ["data", "build", "parts", part, "starting_points"], {}
            ).items()
        }
        if all(x is None for _, x in starting_points.items()):
            starting_points = None
        return {
            "start_time": times[0],
            "end_time": times[1],
            "starting_points": starting_points,
            "layer": int(layer),
        }

    def get_scan_path(self, part, layer):
        """Extracts the scan path file for the database if needed,
        then returns the scanpath file path

        Args:
            part: (str) part name to extract data for
            layer: (int) "layer" corresponding to the time_segment for the part in
                the Myna input file
        """

        # Check if there is a file with info for previous exports, and if previous
        # exports match current start_time and end_time
        matching_file = None
        scan_exports = {}
        part_str = str(part)
        scan_export_name = None
        segment_dict = self.get_segment_details(part, layer)
        if os.path.exists(self.scan_export_dict):
            with open(self.scan_export_dict, "r", encoding="utf-8") as f:
                scan_exports = yaml.safe_load(f)
            for key, entry in scan_exports[part_str].items():
                if (
                    entry["start_time"] == segment_dict["start_time"]
                    and entry["end_time"] == segment_dict["end_time"]
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
            scan_dict = {
                "start_time": segment_dict["start_time"],
                "end_time": segment_dict["end_time"],
            }
            nested_set(scan_exports, [part_str, scan_name], scan_dict)

            # Export scan path data
            scan_export_name = os.path.join(
                self.scanpath_export_dir, part_str, scan_name
            )
            os.makedirs(os.path.dirname(scan_export_name), exist_ok=True)
            df = self.load_build_data(segment_dict=segment_dict, datatype="raw")
            if segment_dict["start_time"] is not None:
                df = df.filter((pl.col("time (s)") >= segment_dict["start_time"]))
            if segment_dict["end_time"] is not None:
                df = df.filter((pl.col("time (s)") <= segment_dict["end_time"]))
            df = self.clean_build_data(df)
            df_myna = self.convert_dataframe_to_myna_scanpath(df)
            df_myna.write_csv(scan_export_name, separator="\t")

            # Write updated scan export dict
            with open(self.scan_export_dict, "w", encoding="utf-8") as f:
                yaml.dump(scan_exports, f, default_flow_style=None)
        else:
            scan_export_name = os.path.join(
                self.scanpath_export_dir, part, matching_file
            )

        return scan_export_name

    def initialize_dataframe(
        self, segment_dict=None, epoch=datetime(1970, 1, 1, tzinfo=None)
    ):
        """Loads the raw x, y, z, and time data from the Pelican simulation data directory.

        Args:
            path: (str) path to the Pelican directory
            segment_dict: (None, {x,y,z,onoff,time}) dictionary describing segment
                start/end conditions
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
            "onoff": pl.Float64,
            "time (s)": pl.Float64,
            "time": pl.Datetime,
        }
        if segment_dict["starting_points"] is None:
            df = pl.DataFrame({key: [] for key in schema}, schema=schema)
        else:
            start_points = segment_dict["starting_points"]
            df = pl.DataFrame(
                {
                    "x (mm)": [start_points["x (mm)"]],
                    "y (mm)": [start_points["y (mm)"]],
                    "z (mm)": [start_points["z (mm)"]],
                    "onoff": [float(start_points["onoff"])],
                    "time (s)": [segment_dict["start_time"]],
                    "time": [epoch + timedelta(seconds=segment_dict["start_time"])],
                },
                schema=schema,
            )
        return df

    def load_build_data(
        self,
        datatype="raw",
        segment_dict=None,
        epoch=datetime(1970, 1, 1, tzinfo=None),
    ):
        """Loads the raw x, y, z, and time data from the Pelican simulation data directory.

        Args:
            datatype: (str) ["raw", "resampled"] type of data to load from Pelican
            epoch: (datetime.datetime instance) datetime object to use as the epoch

        Returns:
            polars.DataFrame instance with the columns defined by `initialize_dataframe()`
        """

        df = self.initialize_dataframe(segment_dict, epoch)
        schema = df.schema
        pelican_datastreams = ["x", "y", "z", "onoff"]
        pelican_names = ["x (mm)", "y (mm)", "z (mm)", "onoff"]

        # Load raw Pelican data
        for stream, name in zip(pelican_datastreams, pelican_names):

            # Get data
            data = zarr.open(
                store=zarr.storage.ZipStore(
                    f"{self.scan_data_dir}/{stream}.zip", mode="r"
                ),
                mode="r",
            )
            locs = np.array(data[f"{datatype}/data"])
            times = np.array(data[f"{datatype}/times"])
            times_datetime = pl.Series(times * 1e6).cast(pl.Duration) + epoch  # s -> us
            blanks = pl.Series(
                name="blanks", values=[None] * len(locs), dtype=pl.Float64
            )

            # Construct DataFrame
            other_keys = set(pelican_names)
            other_keys.discard(name)
            other_keys = [k for k in list(other_keys)]
            df_data = pl.DataFrame(
                {
                    name: locs,
                    other_keys[0]: blanks,
                    other_keys[1]: blanks,
                    other_keys[2]: blanks,
                    "time (s)": times,
                    "time": times_datetime,
                },
                schema=schema,
            )
            df = pl.concat([df, df_data])

        # Ensure only one entry at each time
        other_keys = set(schema)
        other_keys.discard("time")
        df = df.group_by("time").agg([pl.col(col).max() for col in other_keys])
        df = df.select(list(schema)).sort("time")
        return df

    def clean_build_data(self, df):
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
                (
                    pl.col("z (mm)").fill_null(strategy="forward").replace(np.nan, None)
                ).alias("z (mm)"),
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

    def sync(self, component_type, step_types, output_class, files):
        """Sync result files to the database using Pelican-style directory
        and file structure.

        Args:
          component_type: (str) name of workflow component app, i.e., Component.component_application
          step_types: (list of str) list of workflow component types, i.e., Component.types
          output_class: class object for the output file, e.g., Component.output_requirement
          files: List of files to sync for the passed workflow component

        Returns:
          synced_files: list of files that were synced

        For each time segment (i.e., "layer"):
        1. Open the corresponding data file (CSV?, Arrow?, Parquet?, HDF5?)
        2. Get all compatible time-series data from the completed Myna Components
        3. Write all time-series data to the file with each row being a unique time and
           each column corresponding to the variable name (consider overwrite behavior)
        4. Close the file stream
        """
        # Initialize synced file list and write directory
        synced_files = []
        os.makedirs(self.sync_timeseries_dir, exist_ok=True)

        # Check if simulation type is compatible for syncing, else return empty list
        is_part_type = "part" in step_types
        is_layer_type = "layer" in step_types
        is_region_type = ("region" in step_types) or ("build_region" in step_types)
        if not (is_part_type and is_layer_type) or is_region_type:
            return synced_files

        # Define formatters
        def format_segment_prefix(part):
            """Format sync file name"""
            return f"{part}"

        def format_variable_name(name, unit):
            """Format variable name with units"""
            return f"{name} ({unit})"

        def format_time_segment_key(time_start, time_end):
            """Format variable name with units"""
            return f"{time_start}-{time_end} (s)"

        # Get prefixes for each part
        segment_prefixes = []
        for f in files:
            part = os.path.basename(
                os.path.dirname(os.path.dirname(os.path.dirname(f)))
            )
            prefix = format_segment_prefix(part)
            segment_prefixes.append(prefix)

        # For each file in each sync file
        for segment_prefix in segment_prefixes:
            type_prefix = f"myna_{component_type}"
            for f in files:
                part = os.path.basename(
                    os.path.dirname(os.path.dirname(os.path.dirname(f)))
                )
                prefix = format_segment_prefix(part)
                if prefix != segment_prefix:
                    continue

                # Get the output fields
                # Time should always be in "time (s)" field
                try:
                    # Get values for the time series
                    locator, values, value_names, value_units = output_class(
                        f
                    ).get_values_for_sync(mode="temporal")
                    times = locator[0]
                    value_names = [f"{type_prefix}_{name}" for name in value_names]
                    t_start = np.min(times)
                    t_end = np.max(times)
                except (NotImplementedError, KeyError):
                    print("    - Time series sync not implemented for any files")
                    continue

                # Write values to data file:
                # - each value gets its own directory
                # - overwrite any existing values in time range
                for value_data, value_name, value_unit in zip(
                    values, value_names, value_units
                ):
                    # Ensure that the directory for the variable exists
                    export_dir = os.path.join(self.sync_timeseries_dir, value_name)
                    os.makedirs(export_dir, exist_ok=True)

                    # Write the data sync file
                    sync_data_file = os.path.join(export_dir, "data.csv")
                    column_name = format_variable_name(value_name, value_unit)
                    print(f"  - Syncing {sync_data_file}")
                    schema = {
                        "time (s)": Float64,
                        column_name: Float64,
                    }
                    if os.path.exists(sync_data_file):
                        df_sync = pl.read_csv(
                            sync_data_file,
                            schema=schema,
                        )
                        df_sync = df_sync.filter(
                            (pl.col("time (s)") < t_start)
                            | (pl.col("time (s)") > t_end)
                        )
                    else:
                        df_sync = pl.DataFrame({k: [] for k in schema}, schema=schema)
                    df_new_data = pl.DataFrame(
                        {
                            "time (s)": times,
                            column_name: value_data,
                        },
                        schema=schema,
                        strict=False,
                    )
                    df_sync = pl.concat([df_sync, df_new_data]).sort(by="time (s)")
                    df_sync.write_csv(sync_data_file)
                    synced_files.append(sync_data_file)

                    # Write the metadata sync file
                    sync_metadata_file = os.path.join(export_dir, "metadata.yaml")
                    segment_key = format_time_segment_key(t_start, t_end)
                    self.write_segment_sync_metadata(sync_metadata_file, f, segment_key)

        return synced_files
