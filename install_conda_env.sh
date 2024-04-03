#!/bin/bash

# Creates a a conda environment in the
# default conda environment location (CONDA_ENV_PATH)

CONDA_ENV="myna"
source ~/.bashrc
CONDA_ENV_PATH=`conda info --base`
if [ -d $CONDA_ENV_PATH"/envs/$CONDA_ENV" ];
then
  conda activate $CONDA_ENV
else
  conda create --name $CONDA_ENV python=3.8.10
  conda activate $CONDA_ENV
  conda install pip
  conda install -c conda-forge pyyaml
  pip install .
fi
echo ""
