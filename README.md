# Myna

**NOTE**: This repository contains working examples of the workflow, but on-going
development may change directory structures, output files, etc. from previous versions.

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Detailed documentation for Myna can be found at
[https://ornl-mdf.github.io/myna-docs/](https://ornl-mdf.github.io/myna-docs/).

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

Myna is a Python package which requires Python 3. You must install it locally as an
editable package using `pip install -e .`, which is a temporary requirement that will
be changed in future releases. The `myna` package is not on PyPI. To install `myna`
follow the instructions below. For additional details, see
[Getting Started](https://ornl-mdf.github.io/myna-docs/getting_started).

```bash
git clone https://github.com/ORNL-MDF/Myna
cd Myna
pip install -e .
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

If you use Myna in your work, please
[cite this repository](https://zenodo.org/doi/10.5281/zenodo.13345124).
In addition, there is a preliminary work that introduces the concept of leverging the
digital thread for simulations and uses the precursor to Myna:

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
available Peregrine v2023-10 dataset. If you use this data,
please cite:

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
