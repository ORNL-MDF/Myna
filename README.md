# MYNA: Multi-fidelity numerical analysis
*NOTE: This repository contains a working example of the workflow, but on-going development may change directory structures, output files, etc.

## Description
Workflow for setting up and running the **M**ulti-fidelit**Y** **N**umerical **A**nalysis (MYNA) workflow to supplment in situ build data from MDF Peregrine with simulated melt pool and microstructure data.

## Installation
Pre-requisites:
- git
- bash
- anaconda3
- cmake
- OpenFOAM-10

To install all other dependencies, use the `install_workflow.sh` script. 
Default paths are provided, but you can modify the paths to point to existing
component directories or alternative installation directories. A conda
environment named "myna" will be automatically created for use with
the workflow.

## Usage
Before running the workflow, ensure that all settings in `settings.json` are 
correct for your system. File paths for 3DThesis should be specified as absolute 
file paths to ensure the expected behavior, because the 3DThesis executable is
not necessarily located within the `myna` directory. Relative paths may be used
in other parts of the workflow, because the other workflow components are imported
Python modules that are run from within the `myna` directory.

To run the workflow, use the command:
```
conda activate myna
python main.py
```