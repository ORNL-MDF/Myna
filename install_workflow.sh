#/usr/bin/bash

# Notes:
# - assumed behavior is to clone all repositories to the parent 
#   folder of this repo
# - by default a conda environment will be created/activated
#   in the default conda environment location

CONDA_ENV="myna"
if [ -d "$(conda info --base)/envs/$CONDA_ENV" ]; then
  conda activate $CONDA_ENV
else
  conda create --name $CONDA_ENV
  conda activate $CONDA_ENV
fi

# Install/validate 3DThesis repository
THESIS_DIR="$(cd ..; pwd)/3DThesis"
THESIS_EXEC="3DThesis"
chmod 755 ./installers/install_3dthesis.sh
source ./installers/install_3dthesis.sh





