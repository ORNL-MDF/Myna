#!/bin/bash

# Notes:
# - assumed behavior is to clone all repositories to the parent 
#   folder of this repo
# - by default a conda environment will be created/activated
#   in the default conda environment location

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
fi
echo ""

# Install/validate 3DThesis repository
THESIS_DIR="$(cd ..; pwd)/3DThesis"
THESIS_EXEC="3DThesis"
chmod 755 ./installers/install_3dthesis.sh
source ./installers/install_3dthesis.sh
echo ""

# Install/validate autothesis repository
AUTOTHESIS_DIR="$(cd ..; pwd)/autothesis"
chmod 755 ./installers/install_autothesis.sh
source ./installers/install_autothesis.sh
echo ""

# Install/validate calibration repository
CLASSIFICATION_DIR="$(cd ..; pwd)/classification"
chmod 755 ./installers/install_classification.sh
source ./installers/install_classification.sh
echo ""

# Install/validate calibration repository
AUTOFOAM_DIR="$(cd ..; pwd)/autofoam"
chmod 755 ./installers/install_autofoam.sh
source ./installers/install_autofoam.sh
echo ""

