#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from myna.application.cubit.cubit import CubitApp
from myna.application.cubit.vtk_to_exodus_region.app import CubitVtkToExodusApp


class FakeVariable:
    def __init__(self, dtype, size):
        self.dtype = np.dtype(dtype)
        self.data = np.zeros(size, dtype=self.dtype)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value


class FakeExodusDataset:
    def __init__(self, size):
        self.size = size
        self.variables = {}

    def createVariable(self, variable_name, dtype, _dims):
        variable = FakeVariable(dtype, self.size)
        self.variables[variable_name] = variable
        return variable


@pytest.mark.parametrize(
    "segment_size_gb,file_size_gb",
    [
        (None, 0.01),
        (1.0, 2.5),
    ],
)
def test_write_exodus_block_data_supports_single_step_and_segmented_mapping(
    monkeypatch, tmp_path, segment_size_gb, file_size_gb
):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(orientation_segment_gb=segment_size_gb)

    exodus_file = tmp_path / "mesh.e"
    with open(exodus_file, "wb") as f:
        f.truncate(int(file_size_gb * (1024**3)))

    elem_orig_ids = np.array([0, 1, 2, -3, 4], dtype=np.int64)
    df_ref_ids = pd.DataFrame(
        {
            "phi1": [0.1, 0.2, 0.3],
            "Phi": [1.1, 1.2, 1.3],
            "phi2": [2.1, 2.2, 2.3],
        }
    )
    exodus_object = FakeExodusDataset(len(elem_orig_ids))

    app.write_exodus_block_data(
        exodus_object, elem_orig_ids, df_ref_ids, str(exodus_file)
    )

    np.testing.assert_array_equal(
        exodus_object.variables["id_array"].data, elem_orig_ids
    )
    np.testing.assert_allclose(
        exodus_object.variables["euler_bunge_zxz_phi1"].data,
        np.array([0.1, 0.1, 0.2, 0.3, 0.1]),
    )
    np.testing.assert_allclose(
        exodus_object.variables["euler_bunge_zxz_Phi"].data,
        np.array([1.1, 1.1, 1.2, 1.3, 1.1]),
    )
    np.testing.assert_allclose(
        exodus_object.variables["euler_bunge_zxz_phi2"].data,
        np.array([2.1, 2.1, 2.2, 2.3, 2.1]),
    )


def test_get_orientation_chunk_size_rejects_non_positive_segment_size(
    monkeypatch,
):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(orientation_segment_gb=0.0)

    with pytest.raises(ValueError, match="orientation-segment-gb"):
        app.get_orientation_chunk_size("/tmp/unused.e", 10)
