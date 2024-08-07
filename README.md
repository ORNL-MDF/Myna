# Myna

**NOTE**: This repository contains working examples of the workflow, but on-going development may change directory structures, output files, etc. from previous versions.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Description

Myna is a framework to facilitate modeling and simulation workflows based on build data stored in a
digital factory framework, initially developed for the database structure maintained by ORNL MDF's Peregrine tool.

There are several submodules within Myna:

- `workflow`: contains scripts that are run from the command line to execute Myna tasks, such as the command `myna run --input demo.yaml`
- `components`: specifies components in the workflow, such that each component subclass can have specific input & output file and data requirements
- `files`: defines specific file formats that can be specified as either input or output requirements for a component
- `metadata`: defines the specific pieces of meatdata that can be specified as requirements for a component.
Each data subclasses contains the functionality needed to extract specific information from the database
(e.g., MDF Peregrine)

There is also a folder, `interfaces`, that contains interfaces for connecting third-party models to Myna.
These are stored with the directory scheme `interfaces/<component_name>/<interface_name>`.

## Installation

Myna is a Python package which requires Python 3. You can install it locally using `pip install .`,
since the package is not on PyPI. To install `myna` follow the instructions below.

```bash
# clone repository and change directory to cloned repository
git clone https://code.ornl.gov/ygk/myna.git
cd myna

# To install as a static package
pip install .

# Or to install as an editable package
# pip install -e .

# Install with all optional dependencies
pip install -e .[dev]
```

Optional external dependencies include:

- for installer scripts
  - git
  - anaconda3
  - cmake
- for running `examples/demo`
  - 3DThesis
  - AdditiveFOAM
  - ExaCA

If you have anaconda3 installed, you can use the `install_conda_env.sh`
script to create a conda environment named "myna" for use with
the workflow. If you want to install the package as an editable package,
then you will have to change line 17 of the script to be `pip install -e .`

For developers, `pip install -e .[dev]` will install the optional `pytest` dependency,
as well as `black` for autoformatting. The repository currently uses the default `black`
formatting. Test scripts are included with the repository in the "tests" directory.
Examples of using pytest are given below.

```bash
# Default tests for aspects myna Python package installation
pytest

# Include optional tests that check interface functionality
pytest --interfaces
```

## Usage

To run the example Myna workflow use the `myna config` and `myna run` commands and point to a valid YAML input file:

```bash
cd ./examples/solidification_part

# The input.yaml in this example should be modified to match your
# local environment (e.g. file paths)

# Config will update the data fields in input.yaml with the relevant
# metadata and output the updated fields to input_configured.yaml
myna config --input input.yaml --output input_configured.yaml

# Run executes the Myna components specified in input_configured.yaml
myna run --input input_configured.yaml

# Sync stores the results from the Myna run back to the database format
myna sync --input input_configured.yaml

# myna run and myna sync both accept the `--step <step_name>` argument
# to only run/sync a single step or a subset with a comma-separated list
#  `--step [<step_name>,<other_step name>,...]`.
# For example:
myna sync --input input_configured.yaml --step 3dthesis
```

Before running the example workflow, ensure that all dependencies are installed and
that the settings in `input.yaml` are correct for your system. File paths should
be specified as absolute file paths to ensure the expected behavior. To access the interfaces included
with the Myna repository, you can use the `$MYNA_INTERFACE_PATH` environmental variable
in the step components' configure, execute, and postprocess commands within the Myna input file. Both
`$MYNA_INTERFACE_PATH` and `$MYNA_INSTALL_PATH` are set whenever running the Myna scripts or importing
the myna package.

### Available components and interfaces

To get a summary of the available interfaces, use the `myna status` command line script.

```bash
# write myna component and interface status to <filename>
myna status --output status.md
```

The `--output <filename>` argument is optional and defaults to "status.md" if not specified.
Text in the output file is formatted as Markdown.

## Attribution

If you use Myna in your work, please cite this repository. In addition, there is a
preliminary work that introduces the concept of leverging the digital thread for
simulations and uses the precursor to Myna:

```tex
@article{Knapp2023DigitalThread,
   author = {Knapp, Gerald L. and Stump, Benjamin and Scime, Luke and Márquez Rossy, Andrés and Joslin, Chase and Halsey, William and Plotkowski, Alex},
   title = {Leveraging the digital thread for physics-based prediction of microstructure heterogeneity in additively manufactured parts},
   journal = {Additive Manufacturing},
   volume = {78},
   pages = {103861},
   ISSN = {2214-8604},
   DOI = {https://doi.org/10.1016/j.addma.2023.103861},
   year = {2023},
   type = {Journal Article}
}
```

The `resources/Peregrine` directory used for examples are from the publicly
available Peregrine v2023-10 dataset:

```tex
@misc{Peregrine202310,
   author = {Scime, Luke and Snow, Zackary and Ziabari, Amir and Halsey, William and Joslin, Chase and Knapp, Gerry and Coleman, John and Peles, Amra and Graham, Sarah and Marquez Rossy, Andres and Duncan, Ryan and Paquit, Vincent},
   title = {A Co-Registered In-Situ and Ex-Situ Dataset from a Laser Powder Bed Fusion Additive Manufacturing Process (Peregrine v2023-10)},
   DOI = {https://doi.org/10.13139/ORNLNCCS/2008021},
   year = {2023},
   type = {Dataset}
}
```


## Development

See the [guidelines](CONTRIBUTING.md) on how to contribute.


## License

Myna is distributed under an [open source 3-clause BSD license](LICENSE.md).
