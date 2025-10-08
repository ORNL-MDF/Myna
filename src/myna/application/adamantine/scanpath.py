"""Scan path conversion functions

Example adamantine scan path

Number of path segments
5
Mode x y z pmod param
1 0.407867 0.003274 0.001 1.0 1e-6
0 0.414408 -0.003500 0.001 1.0 0.014144
0 0.414944 -0.003350 0.001 1.0 0.001051
0 0.405286 0.006656 0.001  1.0 0.020120
0 0.405654 0.006985 0.001 1.0 0.000988
"""

from pathlib import Path
import polars as pl
from myna.core.metadata.file_scanpath import Scanpath
from myna.application.thesis import get_scan_stats, get_initial_wait_time


def convert_myna_local_scanpath_to_adamantine(
    part: str, layer: str, export_file: str | Path = "scanpath.txt"
) -> dict:
    """Loads the scan path from myna_resources for the specified part and
    layer and returns a dictionary with a summary of the scan path properties
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
        "scan_speed_median": df.filter((pl.col("Mode") == 0) & (pl.col("pmod") > 0))[
            "param"
        ].median(),
    }
    return scan_dict
