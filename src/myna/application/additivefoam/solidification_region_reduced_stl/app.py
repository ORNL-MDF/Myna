#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for the additivefoam/solidification_region_reduced_stl
simulation type. Derives most functionality from the app for
additivefoam/solidification_region_reduced
"""
import os
import yaml
from myna.application import openfoam
from myna.application.additivefoam.solidification_region_reduced import (
    AdditiveFOAMRegionReduced,
)


class AdditiveFOAMRegionReducedSTL(AdditiveFOAMRegionReduced):
    """Simulation type for generating solidification data for specified regions"""

    def __init__(self, name="solidification_region_reduced_stl"):
        super().__init__(name)
        self.stl_mesh_dict_name = "stl_mesh_dict.yaml"

    def configure(self):
        """Configure all cases for the application"""
        # Check for arguments relevant to the configure step
        self.parse_configure_arguments()  # args from the AdditiveFOAMRegionReduced app
        self.parser.add_argument(
            "--scale",
            default=0.001,
            type=float,
            help="Multiple by which to scale the STL file dimensions (default = 0.001, mm -> m)",
        )
        self.args, _ = self.parser.parse_known_args()
        self.mpiargs_to_current()

        # Update derived parameters
        self.set_procs()
        self.update_template_path()

        # Get list of expected output files and iterate through the cases
        mynafiles = self.settings["data"]["output_paths"][self.step_name]
        for mynafile in mynafiles:
            self.configure_case(mynafile)

    def create_coarse_mesh(self, case_dict):
        """Creates the coarse mesh, snapping to the provided STL geometry. If the same
        STL-based mesh has already been generated, then this step is skipped.

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """

        if not self.can_use_existing_stl_mesh_resource(case_dict):

            # Preprocess the STL
            working_stl_path = openfoam.mesh.preprocess_stl(
                case_dict["resource_template_dir"], case_dict["stl"], self.args.scale
            )

            # Generate background mesh
            bb_dict = openfoam.mesh.create_stl_cube_mesh(
                case_dict["resource_template_dir"],
                working_stl_path,
                [self.args.coarse, self.args.coarse, self.args.coarse],
                1.0e-08,
            )

            # Cut background mesh on STL features using snappyHexMeshDict from template
            region_dict = self.settings["data"]["build"]["parts"][case_dict["part"]][
                "regions"
            ][case_dict["region"]]
            openfoam.mesh.extract_stl_features(
                case_dict["resource_template_dir"],
                working_stl_path,
                0,
                [region_dict["x"], region_dict["y"], -1e-6],
            )

            # Create mesh for part
            openfoam.mesh.create_part_mesh(
                case_dict["resource_template_dir"],
                working_stl_path,
                bb_dict,
                app=self,
            )

            # After successful STL mesh generation, write out the mesh dict
            with open(
                os.path.join(
                    case_dict["resource_template_dir"], self.stl_mesh_dict_name
                ),
                mode="w",
                encoding="utf-8",
            ) as f:
                yaml.dump(
                    self.construct_case_mesh_dict(case_dict), f, default_flow_style=None
                )

    def generate_resource_mesh(self, case_dict):
        """Generates the mesh in the resource template directory based on the given
        case and mesh setting dictionaries.

        The STL-based coarse mesh can be reused, but due to the changing layer geometry,
        the region-based refinement should be redone for each layer to avoid assuming
        that each layer has the same cross-section.

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """
        case_dict["stl"] = self.settings["data"]["build"]["parts"][case_dict["part"]][
            "stl"
        ]["file_local"]

        # Copy app template to the resource directory
        self.copy_template_to_dir(case_dict["resource_template_dir"])

        # Generate coarse background mesh
        self.create_coarse_mesh(case_dict)

        # Slice the mesh for the given layer
        layer_thickness = self.settings["data"]["build"]["build_data"][
            "layer_thickness"
        ]["value"]
        height = float(layer_thickness) * float(case_dict["layer"])
        openfoam.mesh.slice_part_mesh(case_dict["resource_template_dir"], height)

        # Refine the layer mesh
        self.refine_layer_mesh(case_dict)
        self.refine_region_mesh(case_dict)

        # After successful mesh generation, write out the mesh dict
        with open(
            os.path.join(case_dict["resource_template_dir"], self.mesh_dict_name),
            mode="w",
            encoding="utf-8",
        ) as f:
            yaml.dump(
                self.construct_case_mesh_dict(case_dict), f, default_flow_style=None
            )

    def can_use_existing_stl_mesh_resource(self, case_dict):
        """Checks if the resource template has STL mesh with matching metadata

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """

        # Set directory for template mesh for the region
        resource_dir = self.get_region_resource_template_dir(
            case_dict["part"], case_dict["region"]
        )
        resource_mesh_dict_path = os.path.join(resource_dir, self.stl_mesh_dict_name)

        # Set STL mesh dictionary for checking if STL mesh compatibility
        mesh_dict = self.construct_part_stl_dict(case_dict)

        # Determine if mesh files in resource directory can be used
        use_existing_mesh = self.has_matching_template_mesh_dict(
            resource_mesh_dict_path, mesh_dict
        )
        return use_existing_mesh

    def construct_part_stl_dict(self, case_dict):
        """Constructs a dictionary with the metadata to describe a unique STL-based
        coarse mesh in the resource template directory.

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """
        mesh_dict = self.construct_case_mesh_dict(case_dict)
        mesh_dict["stl"] = case_dict["stl"]
        return {
            key: mesh_dict.get(key, None)
            for key in ["build", "part", "stl", "coarse_mesh"]
        }
