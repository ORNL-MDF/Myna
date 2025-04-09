# Changelog

## 1.1.0

### New features

- New database types: MynaJSON, PeregrineHDF5, AMBench2022
- Refactor package structure to enable pip install without editable (-e) flag

### Bugfixes and improvements

- Additional info logging during Myna configuration
- Additional utility features in myna.core
- Updates to myna.application apps to add functionality and rely more consistently on the MynaApp class
- Microstructure plotting functions for IPF RGB and Pole Figures added to myna.application.exaca
- Updates to the Peregrine CLI tool
- Handle synonymous keys for process parameter entries in for peregrine and peregrine_hdf5 databases
- Fixed version test

### Minimum dependency version updates

- Minimum supported Python increased to 3.9
- 3DThesis: commit 547a67b (Nov. 8, 2024) or later
- ExaCA: commit 08821ef (Aug. 5, 2024) or later
- AdditiveFOAM: commit b0fa890 (Nov. 12, 2024) or later

## 1.0.0

### Initial features

- Configuration, execution, and syncing for additive manufacturing simulation from database information
- Support for AdditiveFOAM (heat transfer), 3dThesis (heat transfer), ExaCA (microstructure), bnpy (clustering), and OpenFOAM (mesh generation) applications
- Support for the Peregrine database and the Peregrine HDF5 public dataset
- Minimal unit test suite for verifying application usage

### Required dependencies

Those without pip installation include URL. Some dependencies are only used for individual features/applications.

- numpy<2.0
- PyYAML
- pandas
- polars
- vtk
- h5py
- matplotlib
- mistlib (https://github.com/ORNL-MDF/mist.git)
- pyebsd (https://github.com/arthursn/pyebsd.git)
- bnpy (https://github.com/gknapp1/bnpy): forked for numpy bugfix
