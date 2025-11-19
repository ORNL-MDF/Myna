---
title: Getting Started
---

## Installation

### Local Installation

Myna is a Python package which requires Python 3. You must install it locally as an
editable package using `pip install -e .`, which is a temporary requirement that will
be changed in future releases. The `myna` package is not on PyPI. To install `myna`
follow the instructions below.

If you have anaconda3 installed, you can use the `install_conda_env.sh`
script to create a conda environment named "myna" that has Myna installed.

```bash
# clone repository and change directory to cloned repository
git clone https://github.com/ORNL-MDF/Myna
cd Myna

# Myna MUST be installed as an editable package using the `-e` flag
pip install -e .
```

Note that this does not install external, non-Python dependencies. See
[Installation of external dependencies](#installation-of-external-dependencies)
for additional details.

#### Installation for Developers

For developers, `pip install -e .[dev]` will install the optional `pytest` dependency,
as well as `black` for autoformatting. The repository currently uses the default `black`
formatting. Test scripts are included with the repository in the "tests" directory.
Examples of using pytest are given below.

```bash
# Default tests for aspects myna Python package installation
pytest

# Include optional tests that check application functionality
pytest --apps
```

#### Installation of External Dependencies

External, non-Python dependencies are required depending on which applications you
intend to use:

- [3DThesis](https://github.com/ORNL-MDF/3DThesis), commit 646d461 or later
- [AdditiveFOAM](https://github.com/ORNL/AdditiveFOAM), version 1.0 or later
- [ExaCA](https://github.com/LLNL/ExaCA), version 1.3 or later

You should refer to the installation documentation for each of the individual codes for
guidance. You only need to install the external dependencies that you are actually
using.

### Using Docker

There is a Docker container maintained at
[https://github.com/ORNL-MDF/containers](https://github.com/ORNL-MDF/containers).
Details on usage are in the [Docker Container](docker.md) section of this documentation.

## Using Myna

Myna is a framework to facilitate modeling and simulation workflows for additive
manufacturing based on build data stored in a digital factory framework, initially
developed for the database structure maintained by ORNL MDF's Peregrine tool.

There are three top-level submodules within Myna:

- `core`: contains class definitions for metadata, file types, and workflow components,
as well as the core functionality for running Myna workflows
- `application`: implementations of wrappers for various models to satisfy the
requirements of the defined Myna workflow steps
- `database`: implementations of readers for different database types

Examples for the various types of simulation pipelines can be found in the
[Myna examples folder](https://github.com/ORNL-MDF/Myna/tree/main/examples).

In general, these examples can be run by navigating into any of the example directories
and then executing:

```shell
myna config
myna run
myna sync
```

You can also copy the directories out of the Myna repository to run elsewhere. You will
need to update the path to the build under the `data` section of the `input.yaml` file
to point to the correct location. Regardless of your current working directory when
you execute the Myna `config`, `run`, and `sync` commands, the output directory will
be the same directory as the input file.

> [!warning]
> Spaces in the path to the input file may lead to unexpected behavior and/or failed
> simulations. It is known that the OpenFOAM framework does not accept file paths with
> spaces, so any simulation pipeline using OpenFOAM-based tools **must not** use
> spaces in the input file path.

Aside from the command line tools, Myna can also be used as a Python library via
`import myna`. The
[openfoam_meshing_script](https://github.com/ORNL-MDF/Myna/tree/main/examples/openfoam_meshing_script)
example provides a demonstration of importing Myna functions to use in a standalone
Python script.
