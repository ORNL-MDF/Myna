#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#

import os
import glob
import copy
import shutil
import subprocess
import numpy as np
import pandas as pd
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from myna.application.cubit import CubitApp
from myna.application.exaca import read_exaca_vtk_structured_points
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
            "--sculptflags",
            default="-S 2 -CS 5 -LI 2 -OI 150 -df 1 -rb 0.2 -A 7 -SS 5",
            type=str,
            help="(str) flags to pass to `psculpt` to control mesh generation",
        )
        self.args, _ = self.parser.parse_known_args()
        self.exe_psculpt = os.path.join(self.args.cubitpath, "bin", "psculpt")
        self.exe_epu = os.path.join(self.args.cubitpath, "bin", "epu")
        # super().check_exe("psculpt") # TODO: split check_exe functionality

    def mesh_exaca_file(self, exaca_vtk_file, exodus_file):

        case_directory = os.path.dirname(exodus_file)
        exodus_prefix = os.path.basename(exodus_file).replace(".e", "")
        spn_file = os.path.join(case_directory, self.args.spn)
        sample_rate = self.args.downsample
        sculpt_flags = self.args.sculptflags.split(" ")

        # read the ExaCA file and extract the downsampled data
        structured_points = read_exaca_vtk_structured_points(exaca_vtk_file)
        extractor = vtk.vtkExtractVOI()
        extractor.SetInputData(structured_points)
        extractor.SetVOI(structured_points.GetExtent())
        extractor.SetSampleRate(sample_rate, sample_rate, sample_rate)
        extractor.Update()
        data = extractor.GetOutput()
        nx, ny, nz = data.GetDimensions()

        # Get unique integers for each "gid" for .spn file
        gids = vtk_to_numpy(
            data.GetPointData().GetArray("GrainID")
        )  # original list of grain ids
        spn_ids = copy.copy(gids)  # list to renumber grains starting from 1
        unique_gids = np.unique(spn_ids)
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
            with open(
                os.path.join(case_directory, "psculpt.log"), "w", encoding="utf-8"
            ) as f:

                run_in_parallel = (self.args.mpiexec is not None) and (self.args.np > 1)
                if run_in_parallel:
                    sculpt_cmd = [self.args.mpiexec, "-np", self.args.np]
                else:
                    sculpt_cmd = []

                sculpt_cmd.extend(
                    [
                        self.exe_psculpt,
                        "-isp",
                        self.args.spn,
                        "-e",
                        exodus_prefix,
                        "-x",
                        nx,
                        "-y",
                        ny,
                        "-z",
                        nz,
                        *sculpt_flags,
                    ]
                )
                subprocess.run(
                    [str(x) for x in sculpt_cmd],
                    check=True,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )

                # If running in parallel, combine and clean the split mesh
                if run_in_parallel:
                    combine_cmd = [self.exe_epu, "-p", self.args.np, exodus_prefix]
                    subprocess.run(
                        [str(x) for x in combine_cmd],
                        check=True,
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    tmp_files = glob.glob(exodus_prefix + ".e.*")
                    for tmp_file in tmp_files:
                        os.remove(tmp_file)

                # If running in serial, need to rename the output exodus file
                else:
                    shutil.move(exodus_prefix + ".e.1.0", exodus_prefix + ".e")

    def mesh_all_cases(self):
        exaca_files = self.settings["data"]["output_paths"][self.last_step_name]
        exodus_files = self.settings["data"]["output_paths"][self.step_name]
        for exaca_file, exodus_file in zip(exaca_files, exodus_files):
            self.mesh_exaca_file(exaca_file, exodus_file)
