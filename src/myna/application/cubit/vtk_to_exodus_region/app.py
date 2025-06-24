#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Define the application class functionality for the `CubitVtkToExodusApp` class"""
import os
import glob
import copy
import shutil
import json
import subprocess
import numpy as np
from vtk import (  # pylint: disable=no-name-in-module
    vtkStructuredPointsReader,
    vtkExtractVOI,
)
from vtkmodules.util.numpy_support import vtk_to_numpy
from myna.application.cubit import CubitApp
from myna.core.utils import working_directory
from myna.application.exaca import grain_id_to_reference_id, load_grain_ids


class CubitVtkToExodusApp(CubitApp):
    """Myna application to convert an ExaCA VTK file with an ID array into an Exodus
    mesh with the original ID array stored on the corresponding mesh blocks."""

    def __init__(
        self,
        sim_type="vtk_to_exodus",
    ):
        super().__init__(sim_type)
        self.parser.add_argument(
            "--field",
            default="GrainID",
            type=str,
            help="(str) field name of material ids in ExaCA VTK file to use for "
            + "conformal meshing",
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
        self.parser.add_argument(
            "--exacainput",
            default="inputs.json",
            type=str,
            help="(str) name of input file in ExaCA Myna workflow step template"
            + "generated the VTK file",
        )
        self.parse_known_args()

    def get_vtk_file_data(self, vtk_file):
        """Extract the data object from a VTK file
        containing structured points"""
        # read the VTK structured points file and extract the downsampled data
        reader = vtkStructuredPointsReader()
        reader.SetFileName(vtk_file)
        reader.ReadAllScalarsOn()
        reader.Update()
        structured_points = reader.GetOutput()
        extractor = vtkExtractVOI()
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

        # original list of grain ids
        gids = vtk_to_numpy(vtk_data_array.GetPointData().GetArray(self.args.field))

        # Get unique integers for each id in the `field` for .spn file
        # (removes issues in the case where ids are negative)
        spn_ids = copy.copy(gids)  # list to renumber grains starting from 1
        unique_gids = np.unique(spn_ids)
        new_id_dict = {}
        for i, gid in enumerate(unique_gids):
            new_id = i + 1
            spn_ids = np.where(gids == gid, new_id * np.ones_like(gids), spn_ids)
            new_id_dict[new_id] = gid

        # Write out spn file from the 1D array
        spn_file = os.path.join(output_directory, self.args.spn)
        np.savetxt(
            spn_file,
            spn_ids,
            delimiter=" ",
            fmt="%d",
            newline=" ",
        )

        return new_id_dict

    def mesh_vtk_file(self, vtk_file, exodus_file):
        """Meshes a VTK file containing a structured points array based on the specified
        array name (self.args.field)"""

        try:
            from netCDF4 import Dataset  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                'Myna cubit/vtk_to_exodus_region app requires "pip install .[cubit]"'
                + "optional dependencies!"
            ) from exc

        # Pre-process VTK data file
        case_directory = os.path.dirname(exodus_file)
        data = self.get_vtk_file_data(vtk_file)
        nx, ny, nz = data.GetDimensions()
        new_id_dict = self.generate_material_id_file(data, case_directory)

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
                    error_msg = (
                        f"Subprocess exited with return code {returncode}."
                        + "Check {log_file} for details."
                    )
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
                        error_msg = (
                            f"Subprocess exited with return code {returncode}."
                            + " Check {log_file} for details."
                        )
                        raise subprocess.SubprocessError(error_msg)

                    for tmp_file in tmp_files:
                        os.remove(tmp_file)

                # If mesh was generated in serial, will need to rename the output exodus file
                elif len(tmp_files) == 1:
                    shutil.move(tmp_files[0], exodus_prefix + ".e")

                # Append grain ID array and Euler angles to Exodus file
                with Dataset(exodus_prefix + ".e", "r+") as exodus_object:

                    # Get ID array data to write
                    elem_block_ids = exodus_object.variables["eb_prop1"][:]
                    elem_orig_ids = np.array(
                        [new_id_dict[key] for key in elem_block_ids]
                    )

                    # Get Euler angle data to write
                    # > [! note]
                    # > This is the section of the application that makes
                    # > the application ExaCA-specific. Another method of passing
                    # > grain orientation is needed if this app is to be generalized
                    # > to other microstructure simulations.
                    exaca_input_file = os.path.join(
                        os.path.dirname(vtk_file), self.args.exacainput
                    )
                    with open(exaca_input_file, "r", encoding="utf-8") as f:
                        exaca_inputs = json.load(f)
                    ref_id_file = exaca_inputs["GrainOrientationFile"]
                    df_ref_ids = load_grain_ids(ref_id_file)
                    elem_ref_ids = grain_id_to_reference_id(
                        elem_orig_ids, len(df_ref_ids)
                    )
                    df_elems = df_ref_ids.loc[elem_ref_ids]

                    # Create new variables in Exodus file
                    block_data_dict = {
                        "id_array": elem_orig_ids,
                        "euler_bunge_zxz_phi1": df_elems["phi1"].to_numpy(),
                        "euler_bunge_zxz_Phi": df_elems["Phi"].to_numpy(),
                        "euler_bunge_zxz_phi2": df_elems["phi2"].to_numpy(),
                    }
                    for block_data_name, block_data_value in block_data_dict.items():
                        if block_data_name not in exodus_object.variables:
                            block_data = exodus_object.createVariable(
                                block_data_name, block_data_value.dtype, ("num_el_blk",)
                            )

                            # Write data to the new variable
                            block_data[:] = block_data_value

    def mesh_all_cases(self):
        """Generate Exodus mesh files for all cases in the Myna workflow step"""
        vtk_files = self.settings["data"]["output_paths"][self.last_step_name]
        exodus_files = self.settings["data"]["output_paths"][self.step_name]
        for vtk_file, exodus_file in zip(vtk_files, exodus_files):
            if (not os.path.exists(exodus_file)) or (self.args.overwrite):
                self.mesh_vtk_file(vtk_file, exodus_file)
