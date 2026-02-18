#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for the additivefoam/solidification_region_reduced
simulation type
"""

import os
import glob
import shutil
import subprocess
import yaml
from myna.application import openfoam
from myna.application.additivefoam import AdditiveFOAM
from myna.application.additivefoam.path import convert_peregrine_scanpath
from myna.core.utils import working_directory, nested_get


class AdditiveFOAMRegionReduced(AdditiveFOAM):
    """Simulation type for generating solidification data for specified regions"""

    def __init__(self):
        super().__init__()
        self.class_name = "solidification_region_reduced"

        # Define app-specific template file names
        self.mesh_dict_name = "mesh_dict.yaml"

    def parse_configure_arguments(self):
        """Check for arguments relevant to the configure step and update app settings"""
        # Parse app-specific arguments
        self.parser.add_argument(
            "--exaca-mesh",
            default=2.5e-6,
            type=float,
            help="Mesh size for the ExaCA simulations, in meters",
        )
        self.parser.add_argument(
            "--rx",
            default=1e-3,
            type=float,
            help="(float) width of region along X-axis, in meters",
        )
        self.parser.add_argument(
            "--ry",
            default=1e-3,
            type=float,
            help="(float) width of region along Y-axis, in meters",
        )
        self.parser.add_argument(
            "--rz",
            default=1e-3,
            type=float,
            help="(float) depth of region along Z-axis, in meters",
        )
        self.parser.add_argument(
            "--pad-xy",
            default=2e-3,
            type=float,
            help="(float) size of single-refinement mesh region around"
            + " the double-refined region in XY, in meters",
        )
        self.parser.add_argument(
            "--pad-z",
            default=1e-3,
            type=float,
            help="(float) size of single-refinement mesh region around"
            + " the double-refined region in Z, in meters",
        )
        self.parser.add_argument(
            "--pad-sub",
            default=1e-3,
            type=float,
            help="(float) size of coarse mesh cubic region below"
            + " the refined regions in Z, in meters",
        )
        self.parser.add_argument(
            "--coarse",
            default=640e-6,
            type=float,
            help="(float) size of fine mesh, in meters",
        )
        self.parser.add_argument(
            "--refine-layer",
            default=5,
            type=int,
            help="(int) number of region mesh refinement"
            + " levels in layer (each level halves coarse mesh)",
        )
        self.parser.add_argument(
            "--refine-region",
            default=1,
            type=int,
            help="(int) additional refinement of region mesh"
            + " level after layer refinement (each level halves coarse mesh)",
        )
        self.parse_known_args()

    def configure(self):
        """Configure all cases for the application"""
        # Check for arguments relevant to the configure step
        self.parse_configure_arguments()

        # Get list of expected output files and iterate through the cases
        mynafiles = self.settings["data"]["output_paths"][self.step_name]
        for mynafile in mynafiles:
            self.configure_case(mynafile)

    def execute(self):
        """Execute all cases for the application."""
        self.validate_executable("additiveFoam")
        mynafiles = self.settings["data"]["output_paths"][self.step_name]
        processes = []
        for mynafile in mynafiles:
            if (not os.path.exists(mynafile)) or (self.args.overwrite):
                # Execute the case
                process = self.execute_case(mynafile)

                # Handle serial versus batch submission processes
                if self.args.batch:
                    processes.append(process)
                    self.wait_for_open_batch_resources(processes)
                else:
                    self.wait_for_process_success(process)

        # Wait for all jobs to exit successfully if not finished
        if self.args.batch:
            self.wait_for_all_process_success(processes)

    def parse_mynafile_path_to_dict(self, mynafile):
        """Parses the path of the output Myna file into a dictionary containing the
        build, part, region, and layer names.

        Path to the Myna file is expected to be in the format:
            `working_dir/build/part/region/layer/stepname/mynafile`
        """
        dir_parts = os.path.dirname(mynafile).split(os.path.sep)
        case_dict = {
            "build": dir_parts[-5],
            "part": dir_parts[-4],
            "region": dir_parts[-3],
            "layer": dir_parts[-2],
            "case_dir": os.path.dirname(mynafile),
            "mynafile": mynafile,
        }
        return case_dict

    def parse_mynafile_path_to_config_dict(self, mynafile):
        """Parses the path of the output Myna file into a dictionary containing the
        build, part, region, and layer names. Additionally adds mesh information based
        on configuration arguments.

        Path to the Myna file is expected to be in the format:
            `working_dir/build/part/region/layer/stepname/mynafile`
        """
        # Store information about the location of the case within the build
        case_dict = self.parse_mynafile_path_to_dict(mynafile)

        # Store region information
        case_dict["region_dict"] = self.settings["data"]["build"]["parts"][
            case_dict["part"]
        ]["regions"][case_dict["region"]]

        # Store case mesh information
        case_dict["mesh_dict"] = self.construct_case_mesh_dict(case_dict)

        # Store region RVE mesh information
        case_dict["rve_mesh_dict"] = self.construct_rve_mesh_dict(
            case_dict["region_dict"]
        )
        case_dict["rve_mesh_dict"]["bb_dict"] = (
            openfoam.mesh.construct_bounding_box_dict(
                case_dict["rve_mesh_dict"]["region_box"],
                case_dict["rve_mesh_dict"]["rve_pad"],
            )
        )

        # Determine if it is possible to use pre-existing mesh resources
        case_dict["use_existing_mesh"] = self.can_use_existing_mesh_resource(case_dict)
        case_dict["resource_template_dir"] = self.get_region_resource_template_dir(
            case_dict["part"], case_dict["region"]
        )

        return case_dict

    def construct_case_mesh_dict(self, case_dict):
        """Constructs a dictionary that contains all of the information defining the
        mesh for the specified case directory

        Args:
            case_dict: (dict) defines the build, part, and region for a case

        Returns:
            (dict) mesh properties
        """
        return {
            "build": case_dict["build"],
            "part": case_dict["part"],
            "region": case_dict["region"],
            "rx": self.args.rx,
            "ry": self.args.ry,
            "rz": self.args.rz,
            "region_pad": self.args.pad_xy,
            "depth_pad": self.args.pad_z,
            "substrate_pad": self.args.pad_sub,
            "coarse_mesh": self.args.coarse,
            "refine_layer": self.args.refine_layer,
            "refine_region": self.args.refine_region,
        }

    def can_use_existing_mesh_resource(self, case_dict):
        """Checks if there is a valid mesh in the resource template directory.

        This saves time during configuration, because AdditiveFOAM cases for the same
        region in consecutive layers can reuse the same mesh.

        Args:
            case_dict: (dict) defines the build, part, region, and layer names

        Returns:
            (bool) True/False
        """
        # Set directory for template mesh for the region
        resource_dir = self.get_region_resource_template_dir(
            case_dict["part"], case_dict["region"]
        )

        # Set background mesh dictionary for checking if background mesh compatibility
        mesh_dict = self.construct_case_mesh_dict(case_dict)
        resource_mesh_dict_path = os.path.join(resource_dir, self.mesh_dict_name)

        # Determine if mesh files in resource directory can be used
        use_existing_mesh = self.has_matching_template_mesh_dict(
            resource_mesh_dict_path, mesh_dict
        )
        return use_existing_mesh

    def construct_rve_mesh_dict(self, region_dict):
        """Constructs a dictionary with inputs needed for RVE mesh generation

        Args:
            region_dict: (dict) parameters for defining the region location

        Returns:
            (dict) dictionary including bounding box info for layer and RVE refinement
            regions
        """
        rve_mesh_dict = {
            "layer_box": [
                [
                    float(region_dict["x"] - 0.5 * self.args.rx - self.args.pad_xy),
                    float(region_dict["y"] - 0.5 * self.args.ry - self.args.pad_xy),
                    float(-self.args.rz - self.args.pad_z),
                ],
                [
                    float(region_dict["x"] + 0.5 * self.args.rx + self.args.pad_xy),
                    float(region_dict["y"] + 0.5 * self.args.ry + self.args.pad_xy),
                    float(0.0),
                ],
            ],
            "region_box": [
                [
                    float(region_dict["x"] - 0.5 * self.args.rx),
                    float(region_dict["y"] - 0.5 * self.args.ry),
                    float(-self.args.rz),
                ],
                [
                    float(region_dict["x"] + 0.5 * self.args.rx),
                    float(region_dict["y"] + 0.5 * self.args.ry),
                    float(0.0),
                ],
            ],
            "rve_pad": [
                self.args.pad_xy,
                self.args.pad_xy,
                self.args.pad_z + self.args.pad_sub,
            ],
        }
        rve_mesh_dict["bb_dict"] = openfoam.mesh.construct_bounding_box_dict(
            rve_mesh_dict["region_box"],
            rve_mesh_dict["rve_pad"],
        )
        return rve_mesh_dict

    def configure_case(self, mynafile):
        """Create a valid AdditiveFOAM case directory based on the myna_data.yaml file"""

        # Get case settings and region details
        case_dict = self.parse_mynafile_path_to_config_dict(mynafile)

        # If needed, generate the AdditiveFOAM mesh in resource template folder
        if not case_dict["use_existing_mesh"]:
            self.generate_resource_mesh(case_dict)

        # Copy resource template directory to case dir
        shutil.copytree(
            case_dict["resource_template_dir"],
            case_dict["case_dir"],
            dirs_exist_ok=True,
        )

        # Update all other metadata not related to the mesh
        self.update_case_metadata(case_dict)

    def update_case_metadata(self, case_dict):
        """Updates case settings based on Myna information

        Args:
            case_dict: (dict) case information,
                from `self.self.parse_mynafile_path_to_dict()`
        """

        # Extract the laser power (W)
        power = self.settings["data"]["build"]["parts"][case_dict["part"]][
            "laser_power"
        ]["value"]

        # Convert the Myna scan path file
        myna_scanfile = case_dict["region_dict"]["layer_data"][case_dict["layer"]][
            "scanpath"
        ]["file_local"]
        path_name = os.path.basename(myna_scanfile)
        new_scan_path_file = os.path.join(case_dict["case_dir"], "constant", path_name)
        convert_peregrine_scanpath(myna_scanfile, new_scan_path_file, power)

        self.update_beam_spot_size(case_dict["part"], case_dict["case_dir"])
        self.update_material_properties(case_dict["case_dir"])
        self.update_region_start_and_end_times(
            case_dict["case_dir"], case_dict["rve_mesh_dict"]["bb_dict"], path_name
        )
        self.update_heatsource_scanfile(case_dict["case_dir"], path_name)
        self.update_exaca_mesh_size(case_dict["case_dir"])

    def create_coarse_mesh(self, case_dict):
        """Creates the coarse mesh

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """
        # Generate coarse background mesh
        openfoam.mesh.create_cube_mesh(
            case_dict["resource_template_dir"],
            [self.args.coarse, self.args.coarse, self.args.coarse],
            case_dict["rve_mesh_dict"]["region_box"],
            case_dict["rve_mesh_dict"]["rve_pad"],
        )

    def refine_layer_mesh(self, case_dict):
        """Refines the coarse mesh

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """
        # Generate refined mesh in layer thickness
        refine_dict_path = os.path.join(
            case_dict["resource_template_dir"], "system", "refineLayerMeshDict"
        )
        openfoam.mesh.update_parameter(
            refine_dict_path,
            "castellatedMeshControls/refinementRegions/refinementBox/levels",
            f"( ({self.args.refine_layer} {self.args.refine_layer}) )",
        )
        openfoam.mesh.refine_mesh_in_box(
            case_dict["resource_template_dir"],
            case_dict["rve_mesh_dict"]["layer_box"],
            self,
            refine_dict_path,
        )

    def refine_region_mesh(self, case_dict):
        """Refines the already refined layer mesh in the region for the case

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """
        # Generate refined mesh in region
        refine_dict_path = os.path.join(
            case_dict["resource_template_dir"], "system", "refineRegionMeshDict"
        )
        openfoam.mesh.update_parameter(
            refine_dict_path,
            "castellatedMeshControls/refinementRegions/refinementBox/levels",
            f"( ({self.args.refine_region} {self.args.refine_region}) )",
        )
        openfoam.mesh.refine_mesh_in_box(
            case_dict["resource_template_dir"],
            case_dict["rve_mesh_dict"]["region_box"],
            self,
            refine_dict_path,
        )
        self.update_exaca_region_bounds(
            case_dict["resource_template_dir"], case_dict["rve_mesh_dict"]["region_box"]
        )

    def generate_resource_mesh(self, case_dict):
        """Generates the mesh in the resource template directory based on the given
        case and mesh setting dictionaries

        Args:
            case_dict: (dict) describes the case settings,
                from `self.parse_mynafile_path_to_dict()`
        """

        # Copy app template to the resource directory
        self.copy_template_to_case(case_dict["resource_template_dir"])

        # Generate coarse background mesh
        self.create_coarse_mesh(case_dict)

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

    def execute_case(self, mynafile):
        """Run an AdditiveFOAM case using the specified number of cores and batch option

        Args:
            mynafile: (str) path to the expected Myna file for the case

        Returns:
            process: (subprocess.Popen) if `batch==True`, the associated Popen object,
                else `None`
        """

        case_dict = self.parse_mynafile_path_to_dict(mynafile)

        # Update decomposeParDict
        openfoam.mesh.update_parameter(
            f"{case_dict['case_dir']}/system/decomposeParDict",
            "numberOfSubdomains",
            self.args.np,
        )

        with working_directory(case_dict["case_dir"]):
            # Determine if parallel execution
            parallel = self.args.np > 1

            # Decompose case
            if parallel:
                with open("decomposePar.log", "w", encoding="utf-8") as f:
                    process = self.start_subprocess(
                        ["decomposePar", "-force"],
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    self.wait_for_process_success(process)

            # Launch job, using MPI arguments if specified
            with open("additiveFoam.log", "w", encoding="utf-8") as f:
                cmd_args = [self.args.exec]
                if parallel:
                    cmd_args.append("-parallel")
                process = self.start_subprocess_with_mpi_args(
                    cmd_args,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                )

        return process

    def postprocess(self):
        """Postprocesses all cases"""
        _, _, files_are_valid = self.component.get_output_files()
        if not all(files_are_valid):
            mynafiles = self.settings["data"]["output_paths"][self.step_name]
            for mynafile in mynafiles:
                if (not os.path.exists(mynafile)) or (self.args.overwrite):
                    self.postprocess_case(mynafile)

    def postprocess_case(self, mynafile):
        """Postprocess a case to generate the valid Myna file

        Args:
            mynafile: (str) path to the Myna file for the case
        """
        case_dict = self.parse_mynafile_path_to_dict(mynafile)

        with working_directory(case_dict["case_dir"]):
            # Determine if parallel execution
            np = nested_get(
                self.settings["steps"][int(os.environ["MYNA_STEP_INDEX"])][
                    self.step_name
                ],
                ["execute", "np"],
                default_value=1,
            )
            parallel = np > 1
            if parallel:
                with open("reconstructPar.log", "w", encoding="utf-8") as f:
                    # Reconstruct decomposed cases
                    process = self.start_subprocess(
                        ["reconstructPar"],
                        stdout=f,
                        stderr=subprocess.STDOUT,
                    )
                    self.wait_for_process_success(process)

            # Compile solidification data into single file
            with open("myna_postprocess.log", "w", encoding="utf-8") as f:
                with open(mynafile, "w", encoding="utf-8") as mf:
                    # Check data exists
                    datafiles = sorted(glob.glob(f"{case_dict['case_dir']}/ExaCA/*"))
                    if len(datafiles) > 0:
                        # Header
                        process = self.start_subprocess(
                            ["echo", "x (m),y (m),z (m),tm (s),ts (s),cr (k/s)"],
                            stdout=mf,
                            stderr=f,
                        )
                        self.wait_for_process_success(process)
                        # Data
                        process = self.start_subprocess(
                            ["cat", *datafiles],
                            stdout=mf,
                            stderr=f,
                        )
                        self.wait_for_process_success(process)

            # Clean up parallel case files
            if parallel:
                self.clean_parallel_case(case_dict)

    def clean_parallel_case(self, case_dict):
        """Removes parallel files"""

        # Check that the output file is more than 100 kB,
        # i.e., more than just the header, and clean files if safe to do
        # so using shutil.rmtree()
        if (os.path.getsize(case_dict["mynafile"]) > 1e5) and (
            shutil.rmtree.avoids_symlink_attacks
        ):
            # 1. Get list of processor directories and remove recursively
            processor_dirs = glob.glob(
                os.path.join(case_dict["case_dir"], "processor*")
            )
            for pdir in processor_dirs:
                shutil.rmtree(pdir)

            # 2. Remove ExaCA directory recursively
            shutil.rmtree(os.path.join(case_dict["case_dir"], "ExaCA"))
