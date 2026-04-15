---
title: Getting Started
---

## Installation

### Local Installation

Myna is a Python package which requires Python 3.10 or later. The `myna` package is
not on PyPI, so install it from a local clone of this repository. The recommended
workflow uses `uv` and the checked-in `uv.lock` file.

If you have anaconda3 installed, you can use the `install_conda_env.sh`
script to create a conda environment named "myna" that has Myna installed.

```bash
# clone repository and change directory to cloned repository
git clone https://github.com/ORNL-MDF/Myna
cd Myna

# Install uv first: https://docs.astral.sh/uv/getting-started/installation
# Sync the default runtime environment from the checked-in lockfile
uv sync --frozen
```

Note that this does not install external, non-Python dependencies. See
[Installation of external dependencies](#installation-of-external-dependencies)
for additional details.

If you prefer to use `pip`, the following still works:

```bash
pip install -e .
```

#### Installation for Developers

For developers, install the optional `dev` extra so that `pytest`, `ruff`,
`pre-commit`, and the documentation tooling are available:

```bash
uv sync --frozen --extra dev
```

You can add other optional application dependencies only when you need them:

```bash
uv sync --frozen --extra exaca
uv sync --frozen --extra bnpy
```

If you prefer `pip`, the equivalent developer install is:

```bash
pip install -e .[dev]
```

Test scripts are included with the repository in the `tests` directory. Examples of
using `pytest` are given below.

```bash
# Default tests for aspects of the Myna Python package installation
uv run pytest

# Include optional tests that check application functionality
uv run pytest --apps
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
Runnable cases live in
[`examples/cases`](https://github.com/ORNL-MDF/Myna/tree/main/examples/cases),
sample databases live in
[`examples/databases`](https://github.com/ORNL-MDF/Myna/tree/main/examples/databases),
workspace files live in
[`examples/workspaces`](https://github.com/ORNL-MDF/Myna/tree/main/examples/workspaces),
and standalone Python API examples live in
[`examples/utils`](https://github.com/ORNL-MDF/Myna/tree/main/examples/utils).
The
[`examples/cases/README.md`](https://github.com/ORNL-MDF/Myna/blob/main/examples/cases/README.md)
file includes a dependency matrix for each case, and
[`examples/utils/README.md`](https://github.com/ORNL-MDF/Myna/blob/main/examples/utils/README.md)
describes the standalone utility scripts.

In general, these examples can be run by navigating into any of the case directories
and then executing:

```shell
myna config
myna run
myna sync
```

You can also copy the full `examples/` tree out of the Myna repository to run
elsewhere. If you copy an individual case instead, update the path to the build under
the `data` section of the `input.yaml` file and any `myna.workspace` entry to point to
the correct location. Regardless of your current working directory when you execute
the Myna `config`, `run`, and `sync` commands, the output directory will be the same
directory as the input file.

> [!warning]
> Spaces in the path to the input file may lead to unexpected behavior and/or failed
> simulations. It is known that the OpenFOAM framework does not accept file paths with
> spaces, so any simulation pipeline using OpenFOAM-based tools **must not** use
> spaces in the input file path.

Aside from the command line tools, Myna can also be used as a Python library via
`import myna`. The
[openfoam_meshing_script](https://github.com/ORNL-MDF/Myna/tree/main/examples/utils/openfoam_meshing_script)
example provides a demonstration of importing Myna functions to use in a standalone
Python script.
