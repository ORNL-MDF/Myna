#
# Copyright (c) Oak Ridge National Laboratory.
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
import math
import shutil
import json
import shlex
import subprocess
from pathlib import Path
import numpy as np
from vtk import (  # pylint: disable=no-name-in-module
    vtkImageConnectivityFilter,
    vtkStructuredPointsReader,
    vtkExtractVOI,
    vtkXMLImageDataReader,
    vtkXMLImageDataWriter,
)
from vtkmodules.util.numpy_support import vtk_to_numpy
from myna.application.cubit import CubitApp
from myna.core.utils import working_directory
from myna.application.exaca import grain_id_to_reference_id, load_grain_ids


class CubitVtkToExodusApp(CubitApp):
    """Myna application to convert an ExaCA VTK file with an ID array into an Exodus
    mesh with the original ID array stored on the corresponding mesh blocks."""

    def __init__(self):
        super().__init__()
        self.class_name = "vtk_to_exodus"

    def parse_execute_arguments(self):
        self.register_argument(
            "--spn-xyz-order",
            default=5,
            choices=range(6),
            type=int,
            help="Ordering of cells in the SPN file passed to Sculpt "
            + "(0=xyz, 1=xzy, 2=yxz, 3=yzx, 4=zxy, 5=zyx). "
            + "Default 5 matches VTK image point-data flattening with X varying "
            + "fastest and Z slowest.",
        )
        self.register_argument(
            "--field",
            default="GrainID",
            type=str,
            help="(str) field name of material ids in ExaCA VTK file to use for "
            + "conformal meshing",
        )
        self.register_argument(
            "--spn",
            default="material_ids.spn",
            type=str,
            help="output file name containing 1D array of material ids in volume",
        )
        self.register_argument(
            "--downsample",
            default=5,
            type=int,
            help="Sample frequency in XYZ (1 is full dataset)",
        )
        self.register_argument(
            "--sculptflags",
            default="-S 2 -CS 5 -LI 2 -OI 150 -df 1 -rb 0.2 -A 7 -SS 5",
            type=str,
            help="(str) flags to pass to `psculpt` to control mesh generation",
        )
        self.register_argument(
            "--exacainput",
            default="inputs.json",
            type=str,
            help="(str) name of input file in ExaCA Myna workflow step template"
            + "generated the VTK file",
        )
        self.register_argument(
            "--orientation-segment-gb",
            default=None,
            type=float,
            help="Optional target size in GB per orientation-mapping subregion. "
            + "If provided, Euler angle data are mapped and written in serial "
            + "segments sized from the generated Exodus filesize.",
        )
        self.register_argument(
            "--centroid-bbox-size",
            default=None,
            nargs="+",
            type=float,
            help="Optional centroid-centered clipping box size in the input VTK "
            + "coordinate units. Provide either one value for an isotropic box or "
            + "three values for x y z. The clipped volume is cached as a VTI file "
            + "in the cubit case directory and reused when overwrite is False.",
        )
        self.register_argument(
            "--min-grain-voxel-count",
            default=10,
            type=int,
            help="Minimum connected grain-region voxel count to preserve before "
            + "merging it into a neighboring grain.",
        )
        super().parse_execute_arguments()

    @staticmethod
    def load_vtk_image_data(vtk_file):
        """Load legacy VTK structured points or XML image data."""

        suffix = os.path.splitext(vtk_file)[1].lower()
        if suffix == ".vti":
            reader = vtkXMLImageDataReader()
        else:
            reader = vtkStructuredPointsReader()
        reader.SetFileName(vtk_file)
        reader.Update()
        return reader.GetOutput()

    def get_vtk_file_data(self, vtk_file):
        """Extract the downsampled data object from a VTK/VTI image file."""
        structured_points = self.load_vtk_image_data(vtk_file)
        extractor = vtkExtractVOI()
        extractor.SetInputData(structured_points)
        extractor.SetVOI(structured_points.GetExtent())
        extractor.SetSampleRate(
            self.args.downsample, self.args.downsample, self.args.downsample
        )
        extractor.Update()
        return extractor.GetOutput()

    def get_centroid_bbox_size(self):
        """Return the configured centroid clip size as x, y, z lengths."""

        bbox_size = self.args.centroid_bbox_size
        if bbox_size is None:
            return None
        if len(bbox_size) == 1:
            bbox_size = bbox_size * 3
        elif len(bbox_size) != 3:
            raise ValueError(
                "--centroid-bbox-size must provide either one value or three values"
            )
        bbox_size = tuple(float(x) for x in bbox_size)
        if any(x <= 0 for x in bbox_size):
            raise ValueError("--centroid-bbox-size values must be greater than zero")
        return bbox_size

    def get_centroid_clip_voi(self, vtk_data):
        """Return a centroid-centered VOI for the configured bounding box."""

        bbox_size = self.get_centroid_bbox_size()
        if bbox_size is None:
            return None

        bounds = vtk_data.GetBounds()
        center = vtk_data.GetCenter()
        extent = vtk_data.GetExtent()
        origin = vtk_data.GetOrigin()
        spacing = vtk_data.GetSpacing()

        voi = []
        for axis in range(3):
            axis_min = bounds[2 * axis]
            axis_max = bounds[2 * axis + 1]
            clip_half_width = 0.5 * bbox_size[axis]
            clip_min = max(axis_min, center[axis] - clip_half_width)
            clip_max = min(axis_max, center[axis] + clip_half_width)
            axis_spacing = abs(spacing[axis])
            if axis_spacing == 0:
                raise ValueError("Cannot clip VTK image data with zero spacing")
            axis_start = max(
                extent[2 * axis],
                int(np.ceil((clip_min - origin[axis]) / axis_spacing)),
            )
            axis_stop = min(
                extent[2 * axis + 1],
                int(np.floor((clip_max - origin[axis]) / axis_spacing)),
            )
            if axis_start > axis_stop:
                axis_center = int(round((center[axis] - origin[axis]) / axis_spacing))
                axis_center = min(
                    max(axis_center, extent[2 * axis]),
                    extent[2 * axis + 1],
                )
                axis_start = axis_center
                axis_stop = axis_center
            voi.extend([axis_start, axis_stop])
        return tuple(voi)

    @staticmethod
    def get_clipped_vti_path(case_directory):
        """Return the cache path for a centroid-clipped VTI file."""

        return os.path.join(case_directory, "centroid_clip.vti")

    def write_clipped_vti(self, vtk_file, clipped_vti_file):
        """Clip the source image around its centroid and write a cached VTI file."""

        vtk_data = self.load_vtk_image_data(vtk_file)
        voi = self.get_centroid_clip_voi(vtk_data)
        if voi is None:
            raise ValueError(
                "Centroid clip requested without a valid bounding box size"
            )

        extractor = vtkExtractVOI()
        extractor.SetInputData(vtk_data)
        extractor.SetVOI(*voi)
        extractor.Update()

        writer = vtkXMLImageDataWriter()
        writer.SetFileName(clipped_vti_file)
        writer.SetInputData(extractor.GetOutput())
        writer.Write()

    def prepare_vtk_input_file(self, vtk_file, case_directory):
        """Return the input image file to mesh, caching a centroid clip when requested."""

        if self.get_centroid_bbox_size() is None:
            return vtk_file

        clipped_vti_file = self.get_clipped_vti_path(case_directory)
        if os.path.exists(clipped_vti_file) and (not self.args.overwrite):
            return clipped_vti_file

        self.write_clipped_vti(vtk_file, clipped_vti_file)
        return clipped_vti_file

    def generate_material_id_file(self, vtk_data_array, output_directory):
        """Convert a VTK file with a material ID field into a Cubit-compatible material
        id file (.spn) and return dictionary with metadata"""

        gids = self.merge_small_grain_regions(vtk_data_array)

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

    @staticmethod
    def get_overlay_grid_bounds(vtk_data):
        """Return overlay-grid bounds that align Sculpt cells to VTK sample points."""

        origin = vtk_data.GetOrigin()
        spacing = vtk_data.GetSpacing()
        dimensions = vtk_data.GetDimensions()

        bounds = []
        for axis in range(3):
            axis_spacing = float(spacing[axis])
            axis_origin = float(origin[axis])
            axis_dim = int(dimensions[axis])
            if axis_dim <= 0:
                raise ValueError("VTK image data dimensions must be greater than zero")

            axis_min = axis_origin - 0.5 * axis_spacing
            axis_max = axis_origin + (axis_dim - 0.5) * axis_spacing
            bounds.extend([min(axis_min, axis_max), max(axis_min, axis_max)])
        return tuple(bounds)

    @staticmethod
    def format_sculpt_float(value):
        """Format overlay-grid coordinates as plain decimal floats for Sculpt."""

        formatted = format(float(value), ".15f").rstrip("0")
        if formatted.endswith("."):
            formatted += "0"
        return formatted

    @staticmethod
    def get_region_neighbor_counts(grain_ids, region_mask):
        """Count face-adjacent neighboring grain ids for a connected region."""

        neighbor_counts = {}
        for axis in range(3):
            leading = [slice(None)] * 3
            trailing = [slice(None)] * 3
            leading[axis] = slice(1, None)
            trailing[axis] = slice(None, -1)
            leading = tuple(leading)
            trailing = tuple(trailing)

            before_neighbors = grain_ids[trailing][
                region_mask[leading] & ~region_mask[trailing]
            ]
            after_neighbors = grain_ids[leading][
                region_mask[trailing] & ~region_mask[leading]
            ]
            for neighbor_ids in (before_neighbors, after_neighbors):
                if neighbor_ids.size == 0:
                    continue
                neighbor_values, counts = np.unique(neighbor_ids, return_counts=True)
                for neighbor_value, count in zip(neighbor_values, counts):
                    neighbor_counts[neighbor_value] = neighbor_counts.get(
                        neighbor_value, 0
                    ) + int(count)

        return neighbor_counts

    @staticmethod
    def get_replacement_grain_id(neighbor_counts):
        """Choose the neighboring grain id with the strongest shared interface."""

        if len(neighbor_counts) == 0:
            return None

        return min(
            neighbor_counts,
            key=lambda neighbor_gid: (-neighbor_counts[neighbor_gid], neighbor_gid),
        )

    def merge_small_grain_regions(self, vtk_data):
        """Merge small regions and enforce one contiguous region per grain id."""

        min_grain_voxel_count = self.args.min_grain_voxel_count
        if min_grain_voxel_count <= 0:
            raise ValueError("--min-grain-voxel-count must be greater than zero")

        grain_array = vtk_data.GetPointData().GetArray(self.args.field)
        if grain_array is None:
            raise ValueError(f'VTK point-data array "{self.args.field}" was not found')

        gids = vtk_to_numpy(grain_array)
        if gids.size == 0:
            return gids

        nx, ny, nz = vtk_data.GetDimensions()
        grain_ids = gids.reshape((nz, ny, nx))
        vtk_data.GetPointData().SetActiveScalars(self.args.field)

        connectivity_filter = vtkImageConnectivityFilter()
        connectivity_filter.SetInputData(vtk_data)
        connectivity_filter.SetExtractionModeToAllRegions()
        connectivity_filter.SetLabelModeToSizeRank()

        while True:
            merged_region = False
            unique_gids = np.unique(gids)
            for gid in unique_gids:
                grain_array.Modified()
                vtk_data.Modified()
                connectivity_filter.SetScalarRange(gid, gid)
                connectivity_filter.Update()

                if connectivity_filter.GetNumberOfExtractedRegions() == 0:
                    continue

                region_labels = vtk_to_numpy(
                    connectivity_filter.GetOutput().GetPointData().GetScalars()
                ).reshape((nz, ny, nx))
                region_sizes = vtk_to_numpy(
                    connectivity_filter.GetExtractedRegionSizes()
                )
                enforce_single_region = (
                    connectivity_filter.GetNumberOfExtractedRegions() > 1
                )
                for region_label, region_size in enumerate(region_sizes, start=1):
                    if region_size >= min_grain_voxel_count and not (
                        enforce_single_region and region_label > 1
                    ):
                        continue

                    region_mask = region_labels == region_label
                    neighbor_counts = self.get_region_neighbor_counts(
                        grain_ids, region_mask
                    )
                    neighbor_counts.pop(gid, None)
                    replacement_gid = self.get_replacement_grain_id(neighbor_counts)
                    if replacement_gid is None:
                        continue

                    grain_ids[region_mask] = replacement_gid
                    merged_region = True

            if not merged_region:
                break

        return gids

    def build_sculpt_command(self, exodus_prefix, vtk_data):
        """Build the Sculpt command for meshing the SPN volume."""

        nx, ny, nz = vtk_data.GetDimensions()
        sculpt_flag_str = self.args.sculptflags.replace("'", "").replace('"', "")
        sculpt_flags = shlex.split(sculpt_flag_str)
        return [
            self.exe_psculpt,
            "-isp",
            self.args.spn,
            "-spo",
            self.args.spn_xyz_order,
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
        mesh_input_file = self.prepare_vtk_input_file(vtk_file, case_directory)
        data = self.get_vtk_file_data(mesh_input_file)
        new_id_dict = self.generate_material_id_file(data, case_directory)

        # Set exodus variables
        exodus_prefix = os.path.basename(exodus_file).replace(".e", "")
        sculpt_cmd = self.build_sculpt_command(exodus_prefix, data)

        # Change working directory for psculpt, then generate mesh in parallel
        with working_directory(case_directory):
            log_file = os.path.join(case_directory, "psculpt.log")
            with open(log_file, "w", encoding="utf-8") as f:
                process = self.start_subprocess_with_mpi_args(
                    [str(x) for x in sculpt_cmd],
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )
                self.wait_for_process_success(process)

                # If mesh was generated in parallel, combine and clean the split mesh
                tmp_files = glob.glob(exodus_prefix + ".e.*")
                if len(tmp_files) > 1:
                    combine_cmd = [self.exe_epu, "-p", self.args.np, exodus_prefix]
                    process = self.start_subprocess(
                        [str(x) for x in combine_cmd],
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    self.wait_for_process_success(process)

                    for tmp_file in tmp_files:
                        os.remove(tmp_file)

                # If mesh was generated in serial, will need to rename the output exodus file
                elif len(tmp_files) == 1:
                    shutil.move(tmp_files[0], exodus_prefix + ".e")

                # Append grain ID array and Euler angles to Exodus file
                with Dataset(exodus_prefix + ".e", "r+") as exodus_object:
                    elem_block_ids = exodus_object.variables["eb_prop1"][:]
                    elem_orig_ids = np.array(
                        [new_id_dict[key] for key in elem_block_ids]
                    )

                    # > [! note]
                    # > This is the section of the application that makes
                    # > the application ExaCA-specific. Another method of passing
                    # > grain orientation is needed if this app is to be generalized
                    # > to other microstructure simulations.
                    if Path(self.args.exacainput).is_absolute():
                        exaca_input_file = self.args.exacainput
                    else:
                        exaca_input_file = os.path.join(
                            os.path.dirname(vtk_file), self.args.exacainput
                        )
                    with open(exaca_input_file, "r", encoding="utf-8") as f:
                        exaca_inputs = json.load(f)
                    ref_id_file = exaca_inputs["GrainOrientationFile"]
                    df_ref_ids = load_grain_ids(ref_id_file)
                    self.write_exodus_block_data(
                        exodus_object,
                        elem_orig_ids,
                        df_ref_ids,
                        os.path.join(case_directory, exodus_prefix + ".e"),
                    )

    def get_orientation_chunk_size(self, exodus_file, num_blocks):
        """Get the number of blocks to map per serial orientation segment."""

        segment_size_gb = self.args.orientation_segment_gb
        if segment_size_gb is None:
            return None
        if segment_size_gb <= 0:
            raise ValueError("--orientation-segment-gb must be greater than zero")
        if num_blocks <= 0:
            return None

        file_size_gb = os.path.getsize(exodus_file) / (1024.0**3)
        num_segments = max(1, math.ceil(file_size_gb / segment_size_gb))
        return max(1, math.ceil(num_blocks / num_segments))

    @staticmethod
    def ensure_exodus_variable(exodus_object, variable_name, dtype):
        """Ensure an Exodus variable exists and return it."""

        if variable_name not in exodus_object.variables:
            return exodus_object.createVariable(variable_name, dtype, ("num_el_blk",))
        return exodus_object.variables[variable_name]

    def write_exodus_block_data(
        self, exodus_object, elem_orig_ids, df_ref_ids, exodus_file
    ):
        """Write original grain ids and Euler-angle block data to the Exodus file."""

        phi1_ref = df_ref_ids["phi1"].to_numpy()
        Phi_ref = df_ref_ids["Phi"].to_numpy()
        phi2_ref = df_ref_ids["phi2"].to_numpy()
        num_blocks = len(elem_orig_ids)
        chunk_size = self.get_orientation_chunk_size(exodus_file, num_blocks)

        id_array = self.ensure_exodus_variable(
            exodus_object, "id_array", elem_orig_ids.dtype
        )
        phi1_array = self.ensure_exodus_variable(
            exodus_object, "euler_bunge_zxz_phi1", phi1_ref.dtype
        )
        Phi_array = self.ensure_exodus_variable(
            exodus_object, "euler_bunge_zxz_Phi", Phi_ref.dtype
        )
        phi2_array = self.ensure_exodus_variable(
            exodus_object, "euler_bunge_zxz_phi2", phi2_ref.dtype
        )

        if chunk_size is None:
            elem_ref_ids = grain_id_to_reference_id(elem_orig_ids, len(df_ref_ids))
            id_array[:] = elem_orig_ids
            phi1_array[:] = phi1_ref[elem_ref_ids]
            Phi_array[:] = Phi_ref[elem_ref_ids]
            phi2_array[:] = phi2_ref[elem_ref_ids]
            return

        for start in range(0, num_blocks, chunk_size):
            stop = min(num_blocks, start + chunk_size)
            elem_orig_ids_chunk = elem_orig_ids[start:stop]
            elem_ref_ids_chunk = grain_id_to_reference_id(
                elem_orig_ids_chunk, len(df_ref_ids)
            )
            id_array[start:stop] = elem_orig_ids_chunk
            phi1_array[start:stop] = phi1_ref[elem_ref_ids_chunk]
            Phi_array[start:stop] = Phi_ref[elem_ref_ids_chunk]
            phi2_array[start:stop] = phi2_ref[elem_ref_ids_chunk]

    def mesh_all_cases(self):
        """Generate Exodus mesh files for all cases in the Myna workflow step"""
        vtk_files = self.settings["data"]["output_paths"][self.last_step_name]
        exodus_files = self.settings["data"]["output_paths"][self.step_name]
        for vtk_file, exodus_file in zip(vtk_files, exodus_files):
            if (not os.path.exists(exodus_file)) or (self.args.overwrite):
                self.mesh_vtk_file(vtk_file, exodus_file)

    def execute(self):
        """Execute all cubit/vtk_to_exodus_region cases."""
        self.parse_execute_arguments()
        self.mesh_all_cases()
