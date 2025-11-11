#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define base subclass for shared functionality between all adamantine Myna apps"""

from pathlib import Path
from ast import literal_eval
import polars as pl
from myna.core.app import MynaApp
from myna.core.utils import nested_set
from myna.core.metadata.file_scanpath import Scanpath
from myna.application.thesis import get_scan_stats, get_initial_wait_time


class AdamantineApp(MynaApp):
    """Defines a Myna app that uses the adamantine simulation"""

    def __init__(self, name):
        super().__init__(name)
        self.path = str(Path(self.path) / "adamantine")

    def boost_info_file_to_dict(self, input_file: str | Path):
        """Loads a Boost info format adamantine input file to a Python dictionary

        Boost info specification:
            https://www.boost.org/doc/libs/1_73_0/doc/html/property_tree/parsers.html
            #property_tree.parsers.info_parser
        """
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Clean up text
        # - Remove leading/trailing whitespace and empty lines
        # - Delete comments
        lines = [line.strip('\t" "') for line in lines]
        lines = [line.split(";")[0].strip() for line in lines]
        lines = [line for line in lines if line.strip() != ""]

        input_dict = {}
        current_keys = []
        for line in lines:

            # Logically, do not need to know if entering a new dictionary
            if line == "{":
                continue

            # Step up a key
            if line == "}":
                _ = current_keys.pop()

            else:
                split_line = line.split(" ", maxsplit=1)
                if len(split_line) == 1:
                    current_keys.append(split_line[0])
                else:
                    line_key = [split_line[0]]
                    line_literal = split_line[1]
                    if line_literal in ["true", "false"]:
                        line_literal = line_literal.capitalize()
                    try:
                        line_value = literal_eval(line_literal)
                    except ValueError:
                        line_value = line_literal
                    nested_set(input_dict, current_keys + line_key, line_value)

        return input_dict

    def write_dict_to_boost_info_file(self, input_dict: dict, input_file: str | Path):
        """Writes an adamantine input dictionary to the specified file in Boost info
        format"""

        # Assemble lines of the input file
        lines = []
        indent = ""

        def _append_values(lines, value_dict, indent):
            """Recursion for finding keys and values"""
            for _key, _value in value_dict.items():
                if isinstance(_value, dict):
                    lines.append(f"{indent}{_key}\n")
                    lines.append(f"{indent}" + "{\n")
                    lines = _append_values(lines, value_dict[_key], indent + "  ")
                    lines.append(f"{indent}" + "}\n")
                else:
                    line_value = _value
                    if isinstance(line_value, bool):
                        line_value = str(line_value).lower()
                    lines.append(f"{indent}{_key} {line_value}\n")
            return lines

        lines = _append_values(lines, input_dict, indent)

        with open(input_file, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def convert_myna_local_scanpath_to_adamantine(
        self, part: str, layer: str, export_file: str | Path = "scanpath.txt"
    ) -> dict:
        """Loads the scan path from myna_resources for the specified part and
        layer and returns a dictionary with a summary of the scan path properties

        Example adamantine scan path:

        ```
        Number of path segments
        5
        Mode x y z pmod param
        1 0.407867 0.003274 0.001 1.0 1e-6
        0 0.414408 -0.003500 0.001 1.0 0.014144
        0 0.414944 -0.003350 0.001 1.0 0.001051
        0 0.405286 0.006656 0.001  1.0 0.020120
        0 0.405654 0.006985 0.001 1.0 0.000988
        ```
        """

        # Get polars dataframe representation of the Myna scan path
        scanpath_obj = Scanpath(None, part, layer)
        df = scanpath_obj.load_to_dataframe()

        # Map to adamantine columns and units
        df = df.with_columns(
            (pl.col("X(mm)") * 1e-3).alias("x"),
            (pl.col("Y(mm)") * 1e-3).alias("y"),
            (pl.col("Z(mm)") * 1e-3).alias("z"),
        )
        df = df.rename({"Pmod": "pmod", "tParam": "param"})
        df = df.select(["Mode", "x", "y", "z", "pmod", "param"])

        # Check if there is an initial wait time, if so, set to a small number (1e-6 s)
        if (df.select("Mode")[0, 0] == 1) & (df.select("pmod")[0, 0] == 0.0):
            df[0, "param"] = 1e-6

        # Write tabular data
        df.write_csv(export_file, separator=" ")

        # Load scan path to add the header lines
        with open(export_file, "r+", encoding="utf-8") as f:
            scan_data = f.read()
            header = f"Number of path segments\n{len(df)}\n"
            f.seek(0, 0)
            f.write(header + scan_data)

        # Construct output dictionary using the thesis app utilities, given
        # that the Myna scan path is natively in 3DThesis format
        # Units correspond to adamantine units (metric)
        elapsed_time, scan_distance = get_scan_stats(Path(scanpath_obj.file_local))
        initial_wait_time = get_initial_wait_time(Path(scanpath_obj.file_local))
        scan_dict = {
            "myna_scanfile": Path(scanpath_obj.file_local),
            "case_scanfile": Path(export_file),
            "elapsed_time": elapsed_time - initial_wait_time,
            "scan_distance": scan_distance * 1e-3,
            "initial_wait": get_initial_wait_time(Path(scanpath_obj.file_local)),
            "bounds": [
                [df["x"].min(), df["y"].min(), df["z"].min()],
                [df["x"].max(), df["y"].max(), df["z"].max()],
            ],
            "scan_speed_max": df.filter((pl.col("Mode") == 0) & (pl.col("pmod") > 0))[
                "param"
            ].max(),
            "scan_speed_median": df.filter(
                (pl.col("Mode") == 0) & (pl.col("pmod") > 0)
            )["param"].median(),
        }
        return scan_dict
