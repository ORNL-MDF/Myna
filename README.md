# MYNA: Multi-fidelity numerical analysis

*NOTE: Repository is incomplete and currently under development*

## Description
Workflow for setting up and running the **M**ulti-fidelit**Y** **N**umerical **A**nalysis (MYNA) workflow to supplment in situ build data from MDF Peregrine with simulated melt pool and microstructure data.

## Installation
Pre-requisites:
- git
- bash
- anaconda3
- cmake

To install all other dependencies, use the `install_workflow.sh` script. 
Default paths are provided, but you can modify the paths to point to existing
component directories or alternative installation directories. A conda
environment named "myna" will be automatically created for use with
the workflow.

## Usage
Before running the workflow, ensure that all settings in `settings.json` are 
correct for your system. File paths should be specified as absolute file paths
to ensure the expected behavior.

To run the workflow, use the command:
```
conda activate myna
python main.py
```