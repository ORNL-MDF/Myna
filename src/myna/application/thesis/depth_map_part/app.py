#
# Copyright (c) 2024 Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Defines application behavior for the thesis/depth_map_part
simulation type
"""
import os
import glob
import polars as pl
from myna.application.thesis import Thesis, adjust_parameter, read_parameter


class ThesisDepthMapPart(Thesis):
    """Simulation type to simulate a map of the melt pool depth for layers of a part"""

    def __init__(self, name="depth_map_part"):
        super().__init__(name, output_suffix=".Solidification")

    def parse_mynafile_path_to_dict(self, mynafile):
        """Parses the path of the output Myna file into a dictionary containing the
        build, part, and layer names.

        Path to the Myna file is expected to be in the format:
            `working_dir/build/part/layer/stepname/mynafile`
        """
        dir_parts = os.path.dirname(mynafile).split(os.path.sep)
        case_dict = {
            "build": dir_parts[-4],
            "part": dir_parts[-3],
            "layer": dir_parts[-2],
            "case_dir": os.path.dirname(mynafile),
            "mynafile": mynafile,
        }
        return case_dict

    def configure_case(self, myna_file):
        """Configure a valid 3DThesis case from Myna data"""
        # Load case information
        case_info = self.parse_mynafile_path_to_dict(myna_file)

        # Copy template case
        self.copy(case_info["case_dir"])

        # Update case parameters
        self.update_case_parameters(
            case_info["case_dir"], part=case_info["part"], layer=case_info["layer"]
        )

    def configure(self):
        """Configure all simulations associated with the Myna step"""

        # Get expected Myna output files
        myna_files = self.settings["data"]["output_paths"][self.step_name]

        # Run each case
        for myna_file in myna_files:
            self.configure_case(myna_file)

    def execute_case(
        self,
        case_directory,
        proc_list,
        check_for_existing_results=True,
    ):
        """Run the individual 3DThesis case"""
        # Update simulation threads
        settings_file = os.path.join(case_directory, self.case_files["settings"])
        adjust_parameter(settings_file, "MaxThreads", self.args.np)

        # Check if output file exists
        if check_for_existing_results:
            output_files = glob.glob(os.path.join(case_directory, "Data", "*.csv"))
            if (len(output_files) > 0) and not self.args.overwrite:
                print(f"{case_directory} has already been simulated. Skipping.")
                return proc_list or []

        # Run Simulation
        procs = proc_list or []
        procs = self.run_thesis_case(case_directory, procs)

        return procs or []

    def execute(self):
        """Execute all cases for the Myna step"""
        # Get expected Myna output files
        myna_files = self.settings["data"]["output_paths"][self.step_name]

        # Run each case
        proc_list = []
        for case_dir in [os.path.dirname(x) for x in myna_files]:
            proc_list = self.execute_case(case_dir, proc_list)

        # Wait for any remaining processes
        for proc in proc_list:
            pid = proc.pid
            print(f"- {pid=}: Waiting for simulation to complete")
            proc.wait()
            print(f"- {pid=}: Simulation complete")

    def postprocess(self):
        """Postprocess files from the executed 3DThesis cases for the Myna step"""

        # Get expected Myna output files
        myna_files = self.settings["data"]["output_paths"][self.step_name]

        # Post-process results to convert to Myna format
        for mynafile in myna_files:

            # Get list of result file(s), accounting for MPI ranks
            case_directory = os.path.dirname(mynafile)
            case_input_file = os.path.join(case_directory, "ParamInput.txt")
            output_name = read_parameter(case_input_file, "Name")[0]
            result_file_pattern = os.path.join(
                case_directory, "Data", f"{output_name}{self.output_suffix}.Final*.csv"
            )
            output_files = sorted(glob.glob(result_file_pattern))
            for i, filepath in enumerate(output_files):
                df = pl.read_csv(filepath)
                df = df.filter(pl.col("z") == df["z"].max())
                df = df.rename({"x": "x (m)", "y": "y (m)", "depth": "depth (m)"})
                df = df.select(["x (m)", "y (m)", "depth (m)"])
                if i == 0:
                    df_all = df.clone()
                else:
                    df_all = pl.concat([df_all, df])
            df_all.write_csv(mynafile)
