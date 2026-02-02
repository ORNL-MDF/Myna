# Myna

**NOTE**: This repository contains working examples of the workflow, but on-going
development may change directory structures, output files, etc. from previous versions.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Detailed documentation for Myna can be found at
[https://ornl-mdf.github.io/myna-docs/](https://ornl-mdf.github.io/Myna/).

## Description

Myna is a framework to facilitate modeling and simulation workflows for additive
manufacturing based on build data stored in a digital factory framework, initially
developed for the database structure maintained by ORNL MDF's Peregrine tool.

There are three top-level submodules within Myna:

- `core`: contains class definitions for metadata, file types, and workflow components,
as well as the core functionality for running Myna workflows
- `application`: implementations of wrappers for various models to satisfy the
requirements of the defined Myna workflow steps
- `database`: implementations of readers for different database types

## Installation

Myna is a Python package which requires Python 3.10 or later. You must install it locally
because it is not yet on PyPI. To install Myna with either `uv` or `pip` installation
follow the instructions below. For additional details, see
[Getting Started](https://ornl-mdf.github.io/myna-docs/getting_started).

```bash
# Download Myna to your user home directory (assumed in example) or your desired directory
cd $HOME
git clone https://github.com/ORNL-MDF/Myna

# ------------------------ #
# Using uv (modern method) #
# ------------------------ #
# Depends on installing uv: https://docs.astral.sh/uv/getting-started/installation
# First, use uv sync to create project .venv and install dependencies
cd $HOME/Myna
uv sync

# Working inside of the repository source, you will be able to use the following,
# which will automatically update dependencies and changes to the package
cd $HOME/Myna/examples/solidification_part
uv run myna config --output ic.yaml
uv run myna run --input ic.yaml

# You can also activate the Myna project uv virtual environment like classic Python venv
# and it will keep up with any changes to the source code (like `pip install -e`)
. $HOME/Myna/.venv/bin/activate
myna config --output ic.yaml
myna run --input ic.yaml

# To install Myna into an new uv project
cd $HOME
mkdir new-project
cd new-project
uv init
uv add $HOME/Myna # use `--editable` flag if desired, default for uv add is not-editable

# To install Myna as a dependency into an existing uv project
cd $HOME
cd existing-project
uv add $HOME/Myna # use `--editable` flag if desired, default for uv add is not-editable

# -------------------------- #
# Using pip (classic method) #
# -------------------------- #
cd $HOME/Myna
pip install .    # non-editable install
pip install -e . # editable install
```

External, non-Python dependencies are required depending on which applications you
intend to use:

- [3DThesis](https://github.com/ORNL-MDF/3DThesis), commit 646d461 or later
- [AdditiveFOAM](https://github.com/ORNL/AdditiveFOAM), version 1.0
- [ExaCA](https://github.com/LLNL/ExaCA), version 1.3 or later

## Usage

Myna input files define the order of simulation steps and the options for each step.
Optional workspaces can also be created as `.yaml` or `.myna-workspace` files that can
be referenced to share common settings across multiple input files. See
[examples/solidification_part/readme.md](examples/solidification_part/readme.md) for
details on running an example case.

## Attribution

If you use Myna in your work, please cite the version of Myna used via the Zenodo DOI
([link to most recent release](https://zenodo.org/doi/10.5281/zenodo.13345124)).
In addition, please cite any of the relevant journal articles:

- [Knapp et al. (2025)](https://doi.org/10.1016/j.commatsci.2025.114094) describes
  the background for Myna and the 3DThesis, AdditiveFOAM, and ExaCA applications for
  melt pool and microstructure simulations.
- [Knapp et al. (2023)](https://doi.org/10.1016/j.addma.2023.103861) introduces the
  concept of leverging the digital thread for simulations using the precursor to
  Myna and provides details on the solidification data clustering approach.

The `examples/Peregrine` directory used for examples are from the publicly
available Peregrine v2023-10 dataset. If you use this data, please cite
[Scime et al. (2023)](https://doi.ccs.ornl.gov/dataset/be65285a-316d-534d-989e-eacb30cb6e46).

## Development

See the [guidelines](CONTRIBUTING.md) on how to contribute.

## License

Myna is distributed under an [open source 3-clause BSD license](LICENSE.md).
