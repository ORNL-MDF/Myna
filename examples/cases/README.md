# Runnable workflow cases

This directory contains runnable Myna workflow cases.
The cases are organized by workflow rather than by dependency so examples that span
multiple tools stay grouped by outcome instead of by implementation detail.

All cases assume the repository `examples/` layout. If you copy a case to another
location, update the `data.build.path` and `myna.workspace` entries in the copied
input file to match the new location of your databases and workspace files.

Standalone Python API examples live in `../utils/`.

`core only` means the default Myna install is sufficient on the Python side. Optional
dependency groups refer to `uv sync --frozen --extra <group>` or `pip install -e .[group]`.
External tools still need to be installed and configured separately.

| Example | Data source | Optional dependency groups | External tools |
| --- | --- | --- | --- |
| `cluster_solidification` | Peregrine fixture | `bnpy` | 3DThesis |
| `melt_pool_geometry_part` | Peregrine fixture | core only | 3DThesis |
| `melt_pool_geometry_part_heat_accumulation` | Peregrine fixture | core only | 3DThesis |
| `melt_pool_geometry_part_pelican` | Pelican fixture | core only | 3DThesis |
| `microstructure_region` | Peregrine fixture | `exaca` | AdditiveFOAM, ExaCA |
| `microstructure_region_slice` | Peregrine fixture | `exaca` | AdditiveFOAM, ExaCA |
| `openfoam_meshing` | Peregrine fixture | core only | OpenFOAM |
| `rve_part_center` | Peregrine fixture | core only | AdditiveFOAM |
| `solidification_build_region` | Peregrine fixture | core only | 3DThesis |
| `solidification_part` | Peregrine fixture | core only | 3DThesis |
| `solidification_part_hdf5` | PeregrineHDF5 fixture | core only | 3DThesis |
| `solidification_part_json` | MynaJSON fixture | core only | 3DThesis |
| `solidification_part_pelican` | Pelican fixture | core only | 3DThesis |
| `solidification_region_reduced` | Peregrine fixture | core only | AdditiveFOAM |
| `solidification_region_reduced_stl` | Peregrine fixture | core only | AdditiveFOAM |
| `temperature_part` | Peregrine fixture | core only | 3DThesis |
| `temperature_part_pvd` | Pelican fixture | core only | Adamantine |
| `vtk_to_exodus_region` | Peregrine fixture | `exaca`, `cubit`, `deer` | AdditiveFOAM, ExaCA, Cubit, DEER |
