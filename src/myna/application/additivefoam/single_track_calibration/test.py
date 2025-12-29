#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from myna.application.additivefoam.single_track_calibration.app import (
    ExperimentData,
    SimulationData,
    ProcessParameters,
    load_dict_file,
)


def test_experiment_data():
    data = ExperimentData(**load_dict_file("test_exp.yaml"))
    print(data)


def test_simulation_data():
    data = SimulationData(**load_dict_file("test_sim.yaml"))
    print(data.to_polars_df())


if __name__ == "__main__":
    print("SIMULATION DATA:")
    test_simulation_data()
