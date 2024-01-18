# Myna

**NOTE**: This repository contains a working example of the workflow, but on-going development may change directory structures, output files, etc.

## Description

Myna is a framework to facilitate modeling and simulation workflows based on build data stored in a digital factory framework,
specifically for the database structure maintained by ORNL MDF's Peregrine tool.

There are several submodules within Myna:

- `workflow`: contains scripts that are run from the command line to execute Myna tasks, such as the command `myna_run --input demo.yaml`
- `components`: specifies components in the workflow, such that each component subclass can have specific input & output file and data requirements
- `files`: defines specific file formats that can be specified as either input or output requirements for a component
- `peregrine`: defines the specific pieces of information from Peregrine that can be specified as requirements for a component.
Each data subclasses contains the functionality needed to extract specific information from the MDF Peregrine database

There is also a folder, `interfaces`, that contains interfaces for connecting third-party models to Myna.
These are stored with the directory scheme `interfaces/<component_name>/<code_name>`. Note, the `general`
component does not have any specific requirements for data or input & output files; therefore,
it acts as a component class that can be used for workflow tasks that do not fit into any existing `Component` subclasses.

## Installation

Myna is a Python package which requires Python 3. You can install it locally using `pip install .`,
since the package is not on PyPI. To install `myna` follow the instructions below.

```bash
# clone repository and change directory to cloned repository
git clone https://code.ornl.gov/ygk/myna.git
cd myna

# To install as a static package 
pip install .

# To install as an editable package
pip install -e .
```

Optional dependencies include:

- for installer scripts
  - git
  - anaconda3
  - cmake
- for running `examples/demo`
  - OpenFOAM-10
  - 3DThesis
  - classification
  - ExaCA

If you have anaconda3 installed, you can use the `install_conda_env.sh`
script to create a conda environment named "myna" for use with
the workflow. If you want to install the package as an editable package,
then you will have to  line 17 of the script to be `pip install -e .`

For developers, `pip install -e .[dev]` will install the optional `pytest` dependency.
Test scripts are included with the repository in the "tests" directory. Examples of
using pytest are given below.

```bash
# Default tests for aspects myna Python package installation
pytest

# Include optional tests that check interface functionality
pytest --interfaces
```

## Usage

To run the example Myna workflow use the `myna_config` and `myna_run` scripts and point to a valid YAML input file:

```bash
cd ./examples/demo

# this will update the data fields in demo.yaml with the relevant Peregrine data
myna_config --input demo.yaml

# this will run the Myna components specified in demo.yaml
myna_run --input demo.yaml
```

Before running the demo workflow, ensure that all dependencies are installed and
that the settings in `demo.yaml` are correct for your system. File paths should
be specified as absolute file paths to ensure the expected behavior. To access the interfaces included
with the Myna repository, you can use the `$MYNA_INTERFACE_PATH` environmental variable
in the step components' configure, execute, and postprocess commands within the Myna input file. Both
`$MYNA_INTERFACE_PATH` and `$MYNA_INSTALL_PATH` are set whenever running the Myna scripts or importing
the myna package.

### Utility for checking available components and interfaces

To get a summary of the available interfaces, use the `myna_status` command line script.

```bash
# write myna component and interface status to <filename>
myna_status --output status.md
```

The `--output <filename>` argument is optional and defaults to "status.md" if not specified.
Text in the output file is formatted as Markdown.
