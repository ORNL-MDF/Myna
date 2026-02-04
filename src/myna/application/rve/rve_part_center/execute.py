#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.application.rve import RVE
from myna.core.utils import get_adjacent_layer_regions
import polars as pl


def find_part_central_rve(app, part, layerset, rve_dict, rve_id):
    """Update the RVE dictionary with the location of a new RVE at the center of the
    part.

    Args:
        app: RVE(MynaApp) instance
        part: part label
        layerset: list of adjacent layers, e.g., [1,2,3]
        rve_dict: dictionary to update with RVE information
        rve_id: id number to apply to the current RVE

    Returns:
        rve_dict_updated: rve_dict with the found RVE information appended
    """

    # Get the part ID map
    layer = layerset["layer_start"]
    id_map_file = app.settings["data"]["build"]["layer_data"][f"{layer}"][
        "part_id_map"
    ]["file_local"]
    id_map = pl.scan_parquet(id_map_file).collect()

    part_map = id_map.filter(pl.col("part_id") == part)
    xmin = part_map["x (m)"].min()
    ymin = part_map["y (m)"].min()
    xmax = part_map["x (m)"].max()
    ymax = part_map["y (m)"].max()
    xavg = 0.5 * (xmin + xmax)
    yavg = 0.5 * (ymin + ymax)

    rve_dict_updated = rve_dict.copy()
    rve_dict_updated["id"].append(rve_id)
    rve_dict_updated["x (m)"].append(xavg)
    rve_dict_updated["y (m)"].append(yavg)
    rve_dict_updated["layer_starts"].append(layerset["layer_start"])
    rve_dict_updated["layer_ends"].append(layerset["layer_end"])
    rve_dict_updated["part"].append(part)

    return rve_dict_updated


def main():
    class RVEPartCenter(RVE):
        def __init__(self):
            super().__init__()
            self.class_name = "rve_part_center"

    app = RVEPartCenter()

    # Note: There will only ever be one output file, since this is a build-level step
    myna_files = app.settings["data"]["output_paths"][app.step_name]
    for myna_file in myna_files:
        # Get all part names
        parts = app.settings["data"]["build"]["parts"]

        # Get list of all layers in build
        all_layers = []
        for part in parts.keys():
            part_layers = parts[part].get("layers")
            if part_layers is not None:
                all_layers.extend(part_layers)
        all_layers = list(set(all_layers))

        # Get RVE selection
        layersets = get_adjacent_layer_regions(
            app.settings["data"], app.args.max_layers
        )
        rve_dict = {
            "id": [],
            "x (m)": [],
            "y (m)": [],
            "layer_starts": [],
            "layer_ends": [],
            "part": [],
        }
        rve_id = 1
        for part in layersets.keys():
            for layerset in layersets[part]:
                rve_dict = find_part_central_rve(app, part, layerset, rve_dict, rve_id)
                rve_id += 1

        export = pl.DataFrame(
            rve_dict,
            schema={
                "id": int,
                "x (m)": float,
                "y (m)": float,
                "layer_starts": int,
                "layer_ends": int,
                "part": str,
            },
        )
        export.write_csv(myna_file)


if __name__ == "__main__":
    main()
