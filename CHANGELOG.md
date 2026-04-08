# Changelog

All notable changes to this project are documented in this file.

For details on how to update the changelog, see [docs/updating_changelog.md](docs/updating_changelog.md).

## Unreleased

### Changed

- Changed changelog and versioning documentation to standardize release note structure, document update workflow, and make the current project version explicit in [#168](https://github.com/ORNL-MDF/Myna/pull/168) by [@liamnwhite1](https://github.com/liamnwhite1)

---

## 1.1.0 - 2025-04-08

### Release highlights

- Added support for new database types: MynaJSON, PeregrineHDF5, and AMBench2022.
- Improved package structure to support standard `pip install` without the editable (`-e`) flag.
- Updated minimum dependency baselines, including Python 3.9 and newer upstream application commits.

### Added

- Added database type support for MynaJSON, PeregrineHDF5, and AMBench2022.
- Added microstructure plotting functions for IPF RGB and pole figures in `myna.application.exaca`.

### Changed

- Improved package structure to support standard `pip install` without the editable (`-e`) flag.
- Improved info logging during Myna configuration.
- Added utility features in `myna.core`.
- Updated `myna.application` applications to add functionality and rely more consistently on the `MynaApp` class.
- Updated the Peregrine CLI tool.
- Increased the minimum supported Python version to 3.9.
- Updated the minimum 3DThesis dependency to commit `547a67b` (2024-11-08) or later.
- Updated the minimum ExaCA dependency to commit `08821ef` (2024-08-05) or later.
- Updated the minimum AdditiveFOAM dependency to commit `b0fa890` (2024-11-12) or later.

### Fixed

- Fixed handling of synonymous keys for process parameter entries in `peregrine` and `peregrine_hdf5` databases.
- Fixed the version test.

---

## 1.0.0 - 2024-08-19

### Release highlights

- Added initial support for configuring, executing, and syncing additive manufacturing simulations from database information.
- Added integration support for core simulation and analysis applications, including AdditiveFOAM, 3DThesis, ExaCA, bnpy, and OpenFOAM.
- Added support for the Peregrine database and the Peregrine HDF5 public dataset.

### Added

- Added configuration, execution, and syncing for additive manufacturing simulation workflows from database information.
- Added support for AdditiveFOAM (heat transfer), 3DThesis (heat transfer), ExaCA (microstructure), bnpy (clustering), and OpenFOAM (mesh generation) applications.
- Added support for the Peregrine database and the Peregrine HDF5 public dataset.
- Added a minimal unit test suite for verifying application usage.
- Added required dependencies and installation notes, including non-pip sources for feature-specific packages.
- Added dependency requirement `numpy<2.0`.
- Added dependency requirement `PyYAML`.
- Added dependency requirement `pandas`.
- Added dependency requirement `polars`.
- Added dependency requirement `vtk`.
- Added dependency requirement `h5py`.
- Added dependency requirement `matplotlib`.
- Added dependency requirement `mistlib` from [https://github.com/ORNL-MDF/mist.git](https://github.com/ORNL-MDF/mist.git).
- Added dependency requirement `pyebsd` from [https://github.com/arthursn/pyebsd.git](https://github.com/arthursn/pyebsd.git).
- Added dependency requirement `bnpy` from [https://github.com/gknapp1/bnpy](https://github.com/gknapp1/bnpy) (forked for a NumPy bugfix).
