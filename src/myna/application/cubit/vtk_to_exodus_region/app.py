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
import vtk
from vtk.util.numpy_support import vtk_to_numpy
from myna.application.cubit import CubitApp
from myna.core.utils import working_directory


class CubitVtkToExodusApp(CubitApp):
    def __init__(
        self,
        sim_type="vtk_to_exodus",
    ):
        super().__init__(sim_type)
        self.parser.add_argument(
            "--idarray",
            default="GrainID",
            type=str,
            help="(str) array name of material ids in VTK file to use for conformal meshing",
        )
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

        # Check that all needed executables are accessible. This overrides the
        # assumed behavior that each app only has one executable passed through the
        # `--exec` argument, because the user passes a Cubit path
        path_prefix = ""
        if self.args.cubitpath is not None:
            path_prefix = os.path.join(self.args.cubitpath, "bin")
        self.exe_psculpt = os.path.join(path_prefix, "psculpt")
        self.exe_epu = os.path.join(path_prefix, "epu")
        original_executable_arg = self.args.exec
        for executable in [self.exe_psculpt, self.exe_epu]:
            self.args.exec = executable
            self.validate_executable(executable)
        # Set original value back to exec commented out since it is
        if original_executable_arg is not None:
            self.args.exec = (
                f"# (ignored by {self.name}/{self.simulation_type} app) "
                + original_executable_arg
            )
        else:
            self.args.exec = original_executable_arg

    def get_vtk_file_data(self, vtk_file):
        """Extract the data object from a VTK file
        containing structured points"""
        # read the VTK structured points file and extract the downsampled data
        reader = vtk.vtkStructuredPointsReader()
        reader.SetFileName(vtk_file)
        reader.ReadAllScalarsOn()
        reader.Update()
        structured_points = reader.GetOutput()
        extractor = vtk.vtkExtractVOI()
        extractor.SetInputData(structured_points)
        extractor.SetVOI(structured_points.GetExtent())
        extractor.SetSampleRate(
            self.args.downsample, self.args.downsample, self.args.downsample
        )
        extractor.Update()
        return extractor.GetOutput()

    def generate_material_id_file(self, vtk_data_array, output_directory):
        """Convert a VTK file with a material ID field into a Cubit-compatible material
        id file (.spn) and return dictionary with metadata"""

        # Get unique integers for each id in the `idarray` for .spn file
        gids = vtk_to_numpy(
            vtk_data_array.GetPointData().GetArray(self.args.idarray)
        )  # original list of grain ids
        spn_ids = copy.copy(gids)  # list to renumber grains starting from 1
        unique_gids = np.unique(spn_ids)
        for i, gid in enumerate(unique_gids):
            spn_ids = np.where(gids == gid, (i + 1) * np.ones_like(gids), spn_ids)

        # Write out spn file from the 1D array
        spn_file = os.path.join(output_directory, self.args.spn)
        np.savetxt(
            spn_file,
            spn_ids,
            delimiter=" ",
            fmt="%d",
            newline=" ",
        )

        return

    def mesh_vtk_file(self, vtk_file, exodus_file):
        """Meshes a VTK file containing a structured points array based on the specified
        array name (self.args.idarray)"""

        # Pre-process VTK data file
        case_directory = os.path.dirname(exodus_file)
        data = self.get_vtk_file_data(vtk_file)
        nx, ny, nz = data.GetDimensions()
        self.generate_material_id_file(data, case_directory)

        # Set exodus variables
        exodus_prefix = os.path.basename(exodus_file).replace(".e", "")
        sculpt_flags = self.args.sculptflags.split(" ")

        # Change working directory for psculpt, then generate mesh in parallel
        with working_directory(case_directory):
            log_file = os.path.join(case_directory, "psculpt.log")
            with open(log_file, "w", encoding="utf-8") as f:

                sculpt_cmd = [
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
                process = self.start_subprocess_with_MPI_args(
                    [str(x) for x in sculpt_cmd],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )
                returncode = process.wait()
                if returncode != 0:
                    error_msg = f"Subprocess exited with return code {returncode}. Check {log_file} for details."
                    raise subprocess.SubprocessError(error_msg)

                # If mesh was generated in parallel, combine and clean the split mesh
                tmp_files = glob.glob(exodus_prefix + ".e.*")
                if len(tmp_files) > 1:
                    combine_cmd = [self.exe_epu, "-p", self.args.np, exodus_prefix]
                    process = self.start_subprocess(
                        [str(x) for x in combine_cmd],
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    returncode = process.wait()
                    if returncode != 0:
                        error_msg = f"Subprocess exited with return code {returncode}. Check {log_file} for details."
                        raise subprocess.SubprocessError(error_msg)

                    for tmp_file in tmp_files:
                        os.remove(tmp_file)

                # If mesh was generated in serial, will need to rename the output exodus file
                elif len(tmp_files) == 1:
                    shutil.move(tmp_files[0], exodus_prefix + ".e")

    def mesh_all_cases(self):
        vtk_files = self.settings["data"]["output_paths"][self.last_step_name]
        exodus_files = self.settings["data"]["output_paths"][self.step_name]
        for vtk_file, exodus_file in zip(vtk_files, exodus_files):
            if (not os.path.exists(exodus_file)) or (self.args.overwrite):
                self.mesh_vtk_file(vtk_file, exodus_file)
