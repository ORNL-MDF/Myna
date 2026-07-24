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
from vtk import vtkImageData
from vtkmodules.util.numpy_support import numpy_to_vtk

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


class FakeStructuredImage:
    def __init__(self, bounds, center, extent, origin, spacing, dimensions=None):
        self._bounds = bounds
        self._center = center
        self._extent = extent
        self._origin = origin
        self._spacing = spacing
        self._dimensions = dimensions

    def GetBounds(self):
        return self._bounds

    def GetCenter(self):
        return self._center

    def GetExtent(self):
        return self._extent

    def GetOrigin(self):
        return self._origin

    def GetSpacing(self):
        return self._spacing

    def GetDimensions(self):
        return self._dimensions


def make_vtk_image_data(dimensions, grain_ids, field_name="GrainID"):
    image_data = vtkImageData()
    image_data.SetDimensions(*dimensions)
    vtk_array = numpy_to_vtk(np.asarray(grain_ids), deep=1)
    vtk_array.SetName(field_name)
    image_data.GetPointData().SetScalars(vtk_array)
    return image_data


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


def test_merge_small_grain_regions_rejects_non_positive_threshold(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(field="GrainID", min_grain_voxel_count=0)
    vtk_data = make_vtk_image_data((1, 1, 1), np.array([1], dtype=np.int32))

    with pytest.raises(ValueError, match="min-grain-voxel-count"):
        app.merge_small_grain_regions(vtk_data)


def test_merge_small_grain_regions_merges_secondary_disconnected_region(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(field="GrainID", min_grain_voxel_count=1)
    vtk_data = make_vtk_image_data(
        (5, 3, 1),
        np.array(
            [
                1,
                1,
                2,
                1,
                1,
                1,
                1,
                2,
                3,
                3,
                1,
                1,
                2,
                3,
                3,
            ],
            dtype=np.int32,
        ),
    )

    merged = app.merge_small_grain_regions(vtk_data).reshape((1, 3, 5))

    expected = np.array(
        [
            [
                [1, 1, 2, 3, 3],
                [1, 1, 2, 3, 3],
                [1, 1, 2, 3, 3],
            ]
        ],
        dtype=np.int32,
    )
    np.testing.assert_array_equal(merged, expected)


def test_get_replacement_grain_id_prefers_most_shared_faces_then_lowest_id():
    replacement_gid = CubitVtkToExodusApp.get_replacement_grain_id({7: 4, 5: 4, 9: 2})

    assert replacement_gid == 5


def test_get_centroid_bbox_size_supports_scalar_and_xyz(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()

    app.args = SimpleNamespace(centroid_bbox_size=[2.5])
    assert app.get_centroid_bbox_size() == pytest.approx((2.5, 2.5, 2.5))

    app.args = SimpleNamespace(centroid_bbox_size=[2.5, 3.5, 4.5])
    assert app.get_centroid_bbox_size() == pytest.approx((2.5, 3.5, 4.5))


@pytest.mark.parametrize("bbox_size", ([1.0, 2.0], [1.0, -2.0, 3.0]))
def test_get_centroid_bbox_size_rejects_invalid_values(monkeypatch, bbox_size):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(centroid_bbox_size=bbox_size)

    with pytest.raises(ValueError, match="centroid-bbox-size"):
        app.get_centroid_bbox_size()


def test_get_centroid_clip_voi_centers_and_clamps(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(centroid_bbox_size=[4.0, 6.0, 8.0])
    vtk_data = FakeStructuredImage(
        bounds=(0.0, 9.0, 0.0, 19.0, 0.0, 29.0),
        center=(4.5, 9.5, 14.5),
        extent=(0, 9, 0, 19, 0, 29),
        origin=(0.0, 0.0, 0.0),
        spacing=(1.0, 1.0, 1.0),
    )

    voi = app.get_centroid_clip_voi(vtk_data)

    assert voi == (3, 6, 7, 12, 11, 18)


def test_prepare_vtk_input_file_reuses_cached_clip(monkeypatch, tmp_path):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(centroid_bbox_size=[5.0], overwrite=False)

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    cached_vti = case_dir / "centroid_clip.vti"
    cached_vti.write_text("cached", encoding="utf-8")

    write_calls = []
    monkeypatch.setattr(
        app,
        "write_clipped_vti",
        lambda vtk_file, clipped_vti_file: write_calls.append(
            (vtk_file, clipped_vti_file)
        ),
    )

    vtk_input = app.prepare_vtk_input_file("microstructure.vtk", str(case_dir))

    assert vtk_input == str(cached_vti)
    assert write_calls == []


def test_prepare_vtk_input_file_writes_clip_when_needed(monkeypatch, tmp_path):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(centroid_bbox_size=[5.0], overwrite=False)

    case_dir = tmp_path / "case"
    case_dir.mkdir()
    write_calls = []
    monkeypatch.setattr(
        app,
        "write_clipped_vti",
        lambda vtk_file, clipped_vti_file: write_calls.append(
            (vtk_file, clipped_vti_file)
        ),
    )

    vtk_input = app.prepare_vtk_input_file("microstructure.vtk", str(case_dir))

    assert vtk_input == str(case_dir / "centroid_clip.vti")
    assert write_calls == [("microstructure.vtk", str(case_dir / "centroid_clip.vti"))]


def test_get_overlay_grid_bounds_aligns_cells_to_vtk_sample_points(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    vtk_data = FakeStructuredImage(
        bounds=(10.0, 14.0, -5.0, 1.0, 100.0, 108.0),
        center=(12.0, -2.0, 104.0),
        extent=(0, 2, 0, 3, 0, 4),
        origin=(10.0, -5.0, 100.0),
        spacing=(2.0, 2.0, 2.0),
        dimensions=(3, 4, 5),
    )

    bounds = app.get_overlay_grid_bounds(vtk_data)

    assert bounds == pytest.approx((9.0, 15.0, -6.0, 2.0, 99.0, 109.0))


def test_generate_material_id_file_merges_small_disconnected_grain_regions(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.args = SimpleNamespace(
        field="GrainID",
        spn="material_ids.spn",
        min_grain_voxel_count=10,
    )

    vtk_data = make_vtk_image_data(
        (4, 4, 1),
        np.array(
            [
                2,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                1,
                2,
            ],
            dtype=np.int32,
        ),
    )

    new_id_dict = app.generate_material_id_file(vtk_data, str(tmp_path))

    assert new_id_dict == {1: 1}
    spn_ids = np.loadtxt(tmp_path / "material_ids.spn", dtype=np.int32)
    np.testing.assert_array_equal(spn_ids, np.ones(16, dtype=np.int32))


def test_build_sculpt_command_sets_spn_xyz_order(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()
    app.exe_psculpt = "psculpt"
    vtk_data = FakeStructuredImage(
        bounds=(10.0, 14.0, -5.0, 1.0, 100.0, 108.0),
        center=(12.0, -2.0, 104.0),
        extent=(0, 2, 0, 3, 0, 4),
        origin=(10.0, -5.0, 100.0),
        spacing=(2.0, 2.0, 2.0),
        dimensions=(3, 4, 5),
    )
    app.args = SimpleNamespace(
        spn="material_ids.spn",
        spn_xyz_order=5,
        sculptflags="-S 2 -CS 5",
    )

    sculpt_cmd = app.build_sculpt_command("mesh", vtk_data)

    assert sculpt_cmd == [
        "psculpt",
        "-isp",
        "material_ids.spn",
        "-spo",
        5,
        "-e",
        "mesh",
        "-x",
        3,
        "-y",
        4,
        "-z",
        5,
        "-S",
        "2",
        "-CS",
        "5",
    ]


def test_format_sculpt_float_avoids_scientific_notation(monkeypatch):
    monkeypatch.setattr(CubitApp, "_validate_cubit_executables", lambda self: None)
    app = CubitVtkToExodusApp()

    assert app.format_sculpt_float(1.2e-6) == "0.0000012"
    assert app.format_sculpt_float(-3.4e5) == "-340000.0"
