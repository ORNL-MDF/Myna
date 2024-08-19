## Initial features:
- Configuration, execution, and syncing for additive manufacturing simulation from database information
- Support for AdditiveFOAM (heat transfer), 3dThesis (heat transfer), ExaCA (microstructure), bnpy (clustering), and OpenFOAM (mesh generation) applications
- Support for the Peregrine database and the Peregrine HDF5 public dataset
- Minimal unit test suite for verifying application usage

## Required dependencies
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
