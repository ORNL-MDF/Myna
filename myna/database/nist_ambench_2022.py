#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Database class for a directory with NIST AM-Bench 2022 build data"""

from myna.core.db import Database
from myna.core import metadata
import numpy as np
import os
import polars as pl
import h5py
import stl


class AMBench2022DB(Database):
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

    def set_path(self, path):
        """Set the path to the database

        Args:
          path: filepath to the folder containing the downloaded AM-Bench data
        """
        self.path = path
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
            file_database = os.path.join(self.simulation_dir, part, f"part.stl")
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

        SCAN_TIMESTEP = 1e-5  # s

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
                total_time = (entries - 1) * SCAN_TIMESTEP
                times = np.arange(
                    start=0, stop=total_time + SCAN_TIMESTEP, step=SCAN_TIMESTEP
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

                # Drop rows that have both dt_last and dt_next equal to SCAN_TIMESTEP
                abs_tol = 1e-7
                df = df.filter(
                    ((pl.col("dt_last") - SCAN_TIMESTEP).abs() > abs_tol)
                    | ((pl.col("dt_next") - SCAN_TIMESTEP).abs() > abs_tol)
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
                df_scan = pl.DataFrame(
                    {
                        "Mode": pl.Series([], dtype=pl.Int8),
                        "X(mm)": pl.Series([], dtype=pl.Float64),
                        "Y(mm)": pl.Series([], dtype=pl.Float64),
                        "Z(mm)": pl.Series([], dtype=pl.Float64),
                        "Pmod": pl.Series([], dtype=pl.Float64),
                        "tParam": pl.Series([], dtype=pl.Float64),
                    }
                )

                # Iterate through rows sequentially to generate scan path
                time_last_row = None
                for index, row in enumerate(df.iter_rows(named=True)):

                    # If first row in XYPT file, go to point
                    if time_last_row == None:

                        df_row = pl.DataFrame(
                            {
                                "Mode": pl.Series([1], dtype=pl.Int8),
                                "X(mm)": pl.Series([row["X"]], dtype=pl.Float64),
                                "Y(mm)": pl.Series([row["Y"]], dtype=pl.Float64),
                                "Z(mm)": pl.Series([0], dtype=pl.Float64),
                                "Pmod": pl.Series([0], dtype=pl.Float64),
                                "tParam": pl.Series([0], dtype=pl.Float64),
                            }
                        )

                    # If the next time is farther away than the SCAN_TIMESTEP, go to start point
                    elif np.abs(row["dt_next"] - SCAN_TIMESTEP) > abs_tol:

                        df_row = pl.DataFrame(
                            {
                                "Mode": pl.Series([1], dtype=pl.Int8),
                                "X(mm)": pl.Series([row["X"]], dtype=pl.Float64),
                                "Y(mm)": pl.Series([row["Y"]], dtype=pl.Float64),
                                "Z(mm)": pl.Series([0], dtype=pl.Float64),
                                "Pmod": pl.Series([0], dtype=pl.Float64),
                                "tParam": pl.Series([row["dt_last"]], dtype=pl.Float64),
                            }
                        )

                    # If the last time was longer ago than the SCAN_TIMESTEP, go raster to point
                    elif np.abs(row["dt_last"] - SCAN_TIMESTEP) > abs_tol:

                        df_row = pl.DataFrame(
                            {
                                "Mode": pl.Series([0], dtype=pl.Int8),
                                "X(mm)": pl.Series([row["X"]], dtype=pl.Float64),
                                "Y(mm)": pl.Series([row["Y"]], dtype=pl.Float64),
                                "Z(mm)": pl.Series([0], dtype=pl.Float64),
                                "Pmod": pl.Series([power], dtype=pl.Float64),
                                "tParam": pl.Series(
                                    [
                                        row["dist_to_last"]
                                        * 1e-3
                                        / (row["Time(s)"] - time_last_row)
                                    ],
                                    dtype=pl.Float64,
                                ),
                            }
                        )

                    df_scan = df_scan.vstack(df_row)
                    time_last_row = row["Time(s)"]

                # Export to .txt file with tab-separated values
                df_scan.write_csv(file_database, separator="\t")

        return file_database

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
            xmin, xmax, ymin, ymax = [-45.0, 45.1, 42.561, 47.496]
        elif part_name_format(part) == "G2":
            xmin, xmax, ymin, ymax = [-45.0, 45.1, -47.439, -42.504]
        elif part_name_format(part) == "P1":
            xmin, xmax, ymin, ymax = [-34.499, 40.599, 28.244, 33.25]
        elif part_name_format(part) == "P2":
            xmin, xmax, ymin, ymax = [-36.499, 38.599, 7.744, 12.75]
        elif part_name_format(part) == "P3":
            xmin, xmax, ymin, ymax = [-38.499, 36.599, -12.756, -7.75]
        elif part_name_format(part) == "P4":
            xmin, xmax, ymin, ymax = [-40.499, 34.599, -33.256, -28.25]

        return [xmin, xmax, ymin, ymax]
