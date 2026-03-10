#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
import polars as pl
from myna.core.utils import get_adjacent_layer_regions
from myna.core.workflow import config, write_input
from myna.application.rve import RVE


class RVEPartCenter(RVE):
    def __init__(self):
        super().__init__()
        self.class_name = "rve_part_center"

    def find_part_central_rve(self, part, layerset, rve_dict, rve_id):
        """Update the RVE dictionary with a new center point for the given part."""
        layer = layerset["layer_start"]
        id_map_file = self.settings["data"]["build"]["layer_data"][f"{layer}"][
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

    def execute(self):
        """Execute RVE selection for all output files."""
        self.parse_execute_arguments()
        myna_files = self.settings["data"]["output_paths"][self.step_name]
        for myna_file in myna_files:
            layersets = get_adjacent_layer_regions(
                self.settings["data"], self.args.max_layers
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
                    rve_dict = self.find_part_central_rve(
                        part, layerset, rve_dict, rve_id
                    )
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

    def postprocess(self):
        """Populate region metadata from the selected RVEs."""
        self.parse_postprocess_arguments()
        myna_files = self.settings["data"]["output_paths"][self.step_name]
        for part in self.settings["data"]["build"]["parts"]:
            values = self.settings["data"]["build"]["parts"][part].get("regions")
            if values is None:
                self.settings["data"]["build"]["parts"][part]["regions"] = {}

        for myna_file in myna_files:
            df = pl.read_csv(myna_file)
            for row in df.iter_rows(named=True):
                part = str(row["part"])
                region = f"rve_{row['id']}"
                self.settings["data"]["build"]["parts"][part]["regions"][region] = {
                    "x": row["x (m)"],
                    "y": row["y (m)"],
                    "layer_starts": row["layer_starts"],
                    "layer_ends": row["layer_ends"],
                    "layers": [
                        x
                        for x in range(
                            int(row["layer_starts"]), int(row["layer_ends"]) + 1
                        )
                    ],
                }

        write_input(self.settings, self.input_file)
        config.config(self.input_file)
