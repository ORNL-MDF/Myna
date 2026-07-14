#!/usr/bin/env python3
#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Plot Myna solidification CSV outputs as 2D images."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import yaml

from myna.core.utils import downsample_to_image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Plot Myna FileGV solidification outputs under myna_output using "
            "the same downsample_to_image projection used by Myna database sync."
        )
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("myna_output"),
        help="Root directory to search for FileGV CSV outputs (default: %(default)s).",
    )
    parser.add_argument(
        "--csv",
        dest="csv_files",
        action="append",
        type=Path,
        help="Specific FileGV CSV to plot. May be passed more than once.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=None,
        help="Override square image size in pixels. Default reads Peregrine buildmeta.",
    )
    parser.add_argument(
        "--plate-size",
        type=float,
        default=None,
        help="Override square plate size in meters. Default reads Peregrine buildmeta.",
    )
    parser.add_argument(
        "--bottom-left",
        nargs=2,
        type=float,
        metavar=("X_M", "Y_M"),
        default=(0.0, 0.0),
        help="Bottom-left build coordinate in meters (default: %(default)s).",
    )
    parser.add_argument(
        "--mode",
        choices=("max", "min", "average"),
        default="average",
        help="Downsampling mode passed to downsample_to_image (default: %(default)s).",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Display figures interactively in addition to saving them.",
    )
    return parser.parse_args()


def find_csv_files(output_root: Path, explicit_csvs: list[Path] | None) -> list[Path]:
    if explicit_csvs:
        csv_files = [path.resolve() for path in explicit_csvs]
    else:
        csv_files = sorted(output_root.rglob("*FileGV.csv"))
    if not csv_files:
        raise FileNotFoundError(
            f"No Myna FileGV CSV outputs found under '{output_root.resolve()}'."
        )
    return csv_files


def read_gv_csv(
    csv_path: Path,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    x_values = []
    y_values = []
    g_values = []
    v_values = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"x (m)", "y (m)", "G (K/m)", "V (m/s)"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(
                f"{csv_path} is missing one or more required FileGV columns: "
                f"{sorted(required)}"
            )
        for row in reader:
            x_values.append(float(row["x (m)"]))
            y_values.append(float(row["y (m)"]))
            g_values.append(float(row["G (K/m)"]))
            v_values.append(float(row["V (m/s)"]))
    return (
        np.asarray(x_values),
        np.asarray(y_values),
        np.asarray(g_values),
        np.asarray(v_values),
    )


def load_buildmeta(csv_path: Path) -> tuple[float, int]:
    case_dir = csv_path.parent
    myna_data_path = case_dir / "myna_data.yaml"
    with myna_data_path.open(encoding="utf-8") as handle:
        myna_data = yaml.safe_load(handle)

    build = myna_data["build"]
    datatype = build["datatype"]
    if datatype != "Peregrine":
        raise ValueError(
            f"{csv_path} references datatype '{datatype}', but this plotting script "
            "currently supports Peregrine metadata discovery only."
        )

    workflow_input = Path(myna_data["myna"]["configure"]["input-file"]).resolve()
    build_root = (workflow_input.parent / build["path"]).resolve()
    buildmeta_path = build_root / datatype / "simulation" / "meltpool" / "buildmeta.npz"
    with np.load(buildmeta_path, allow_pickle=True) as buildmeta:
        plate_size = float(buildmeta["actual_size"][0]) * 1e-3
        image_size = int(buildmeta["image_size"][0])
    return plate_size, image_size


def resolve_image_settings(
    csv_path: Path, image_size: int | None, plate_size: float | None
) -> tuple[float, int]:
    meta_plate_size, meta_image_size = load_buildmeta(csv_path)
    return (
        meta_plate_size if plate_size is None else plate_size,
        meta_image_size if image_size is None else image_size,
    )


def make_plot(
    csv_path: Path,
    image_size: int | None,
    plate_size: float | None,
    bottom_left: tuple[float, float],
    mode: str,
    show: bool,
) -> Path:
    x_values, y_values, g_values, v_values = read_gv_csv(csv_path)
    plate_size_value, image_size_value = resolve_image_settings(
        csv_path, image_size, plate_size
    )
    extent = [
        bottom_left[0],
        bottom_left[0] + plate_size_value,
        bottom_left[1],
        bottom_left[1] + plate_size_value,
    ]

    extent = [
        np.min(x_values) - 1e-3,
        np.max(x_values) + 1e-3,
        np.min(y_values) - 1e-3,
        np.max(y_values) + 1e-3,
    ]
    image_size_value = 100
    plate_size_value = max(extent[1] - extent[0], extent[3] - extent[2])
    bottom_left = (extent[0], extent[2])

    images = {
        "G (K/m)": downsample_to_image(
            data_x=x_values,
            data_y=y_values,
            values=g_values,
            image_size=image_size_value,
            plate_size=plate_size_value,
            bottom_left=list(bottom_left),
            mode=mode,
        ),
        "V (m/s)": downsample_to_image(
            data_x=x_values,
            data_y=y_values,
            values=v_values,
            image_size=image_size_value,
            plate_size=plate_size_value,
            bottom_left=list(bottom_left),
            mode=mode,
        ),
    }

    figure, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)
    for axis, (title, image) in zip(axes, images.items(), strict=True):
        plot = axis.imshow(image, origin="lower", extent=extent, cmap="viridis")
        axis.set_title(title)
        axis.set_xlabel("x (m)")
        axis.set_ylabel("y (m)")
        figure.colorbar(plot, ax=axis, shrink=0.85)

    figure.suptitle(csv_path.stem)
    output_path = csv_path.with_name(f"{csv_path.stem}-plot.png")
    figure.savefig(output_path, dpi=200)
    if show:
        plt.show()
    plt.close(figure)
    return output_path


def main() -> int:
    args = parse_args()
    csv_files = find_csv_files(args.output_root, args.csv_files)
    for csv_path in csv_files:
        output_path = make_plot(
            csv_path=csv_path,
            image_size=args.image_size,
            plate_size=args.plate_size,
            bottom_left=tuple(args.bottom_left),
            mode=args.mode,
            show=args.show,
        )
        print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
