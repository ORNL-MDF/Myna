# Myna

**NOTE**: This repository contains working examples of the workflow, but on-going
development may change directory structures, output files, etc. from previous versions.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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

Myna is a Python package which requires Python 3. You can install it locally using `pip install .`,
since the package is not on PyPI. To install `myna` follow the instructions below.

```bash
# clone repository and change directory to cloned repository
git clone https://github.com/ORNL-MDF/Myna
cd myna

# To install as a static package
pip install .

# Or to install as an editable package
pip install -e .

# Install with all optional dependencies
pip install -e .[dev]
```

External dependencies are required depending on which applications you wish to use:

- [3DThesis](https://gitlab.com/JamieStumpORNL/3DThesis)
- [AdditiveFOAM](https://github.com/ORNL/AdditiveFOAM)
- [ExaCA](https://github.com/LLNL/ExaCA)

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

# Include optional tests that check application functionality
pytest --apps
```

## Usage

Myna input files define the order of simulation steps and the options for each step.
Optional workspaces can also be created as `.yaml` or `.myna-workspace` files that can
be referenced to share common settings across multiple input files. See
[examples/solidification_part/readme.md](examples/solidification_part/readme.md) for
more details. Note: Before running this example, ensure that the external 3DThesis
dependency is installed and that the 3DThesis executable is in your path.

### Available components and applications

To get a summary of the available classes and applications, use the `myna status`
command line tool.

```bash
# write myna component and application status to <filename>
myna status --output status.md
```

The `--output <filename>` argument is optional and defaults to "status.md" if not
specified. Text in the output file is formatted as Markdown.

## Attribution

If you use Myna in your work, please [cite this repository](https://zenodo.org/doi/10.5281/zenodo.13345124). In addition, there is a
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
