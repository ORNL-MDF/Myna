#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#

import os
import subprocess
import numpy as np
import pandas as pd
from myna.application.cubit import CubitApp
from myna.core.utils import working_directory


class CubitVtkToExodusApp(CubitApp):
    def __init__(
        self,
        sim_type="vtk_to_exodus",
    ):
        super().__init__(sim_type)
        self.parser.add_argument(
            "--spn",
            default="material_ids.spn",
            type=str,
            help="output file name containing 1D array of material ids in volume",
        )
        self.parser.add_argument(
            "--downsample",
            default=5,
            type=int,
            help="Sample frequency in XYZ (1 is full dataset)",
        )
        self.parser.add_argument(
            "--epuexec",
            default="epu",
            type=str,
            help="Path to the `epu` executable",
        )
        self.args, _ = self.parser.parse_known_args()
        super().check_exe("psculpt")

    def mesh_exaca_file(self, exaca_file, exodus_file):

        case_directory = os.path.dirname(exaca_file)
        exodus_prefix = os.path.basename(exodus_file).replace(".e", "")
        spn_file = os.path.join(case_directory, self.args["spn"])
        downsample = self.args["downsample"]

        # read the ExaCA file
        data = pd.read_csv(exaca_file, usecols=["X (m)", "Y (m)", "Z (m)", "gid"])

        # downsample the data
        xs = data["X (m)"].unique()
        ys = data["Y (m)"].unique()
        zs = data["Z (m)"].unique()
        data = data[data["X (m)"].isin(xs[::downsample])]
        data = data[data["Y (m)"].isin(ys[::downsample])]
        data = data[data["Z (m)"].isin(zs[::downsample])]

        # get data dimensions
        Nx = int(data["X (m)"].nunique())
        Ny = int(data["Y (m)"].nunique())
        Nz = int(data["Z (m)"].nunique())

        # sort the data
        data = data.sort_values(by=["X (m)", "Y (m)", "Z (m)"])

        # Get unique integers for each "gid" for .spn file
        unique_gids = data["gid"].unique()
        spn_ids = data["gid"].to_numpy()
        gids = data["gid"].to_numpy()
        for i, gid in enumerate(unique_gids):
            spn_ids = np.where(gids == gid, (i + 1) * np.ones_like(gids), spn_ids)

        # Write out spn file from the 1D array
        np.savetxt(
            spn_file,
            spn_ids,
            delimiter=" ",
            fmt="%d",
            newline=" ",
        )

        # Change working directory for psculpt, then generate mesh in parallel
        with working_directory(case_directory):
            sculpt_cmd = [
                self.args.mpiexec,
                "-np",
                self.args.np,
                self.args.exe,
                "-isp",
                self.args.spn,
                "-e",
                exodus_prefix,
                "-x",
                Nx,
                "-y",
                Ny,
                "-z",
                Nz,
                "-S",
                2,
                "-CS",
                5,
                "-LI",
                2,
                "-OI",
                150,
                "-df",
                1,
                "-rb",
                0.2,
                "-A",
                7,
                "-SS",
                5,
            ]
            subprocess.run(sculpt_cmd, check=True)

            # combine and clean the split mesh
            combine_cmd = [self.args.epuexec, "-p", self.args.np, exodus_prefix]
            subprocess.run(combine_cmd, check=True)
            clean_cmd = ["rm", self.args.meshprefix + ".*"]
            subprocess.run(clean_cmd, check=True)

    def mesh_all_cases(self):
        exaca_files = self.settings["data"]["output_paths"][self.last_step_name]
        exodus_files = self.settings["data"]["output_paths"][self.step_name]
        for exaca_file, exodus_file in zip(exaca_files, exodus_files):
            self.mesh_exaca_file(exaca_file, exodus_file)
