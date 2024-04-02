#!/bin/bash

# Check if need to set default directory values
if [ -z "$AUTOFOAM_DIR" ]; then
  AUTOFOAM_DIR="$(cd ../..; pwd)/autofoam"
fi

# Clone and build if necessary
ROOT_DIR=$(pwd)
TARGET_COMMIT="0c296f36f773d4fd26d47aea65f2328bc08903d8"
if [ -d "$AUTOFOAM_DIR" ]; then
  echo "$AUTOFOAM_DIR already exists."
  cd $AUTOFOAM_DIR
  COMMIT=$(git rev-parse HEAD)
  if [ $COMMIT != $TARGET_COMMIT ]; then
    echo "WARNING: Version of target autofoam repository"
    echo "does not match recommended value"
    echo "  -- Recommended commit: $TARGET_COMMIT"
    echo "  -- Specified repo commit: $COMMIT"
  fi
else
  echo "Cloning autofoam repository to $AUTOFOAM_DIR"
  cd ..
  git clone https://code.ornl.gov/8s2/autofoam.git
  git branch -u origin/remove-foam-dep remove-foam-dep
  git switch remove-foam-dep
  git checkout $TARGET_COMMIT
fi

# Install/verify package install
PACKAGE=`conda list | awk -F"[ ',]+" '/^autofoam/{print $1}'`
if [ $PACKAGE = "autofoam" ];
then
  echo "autofoam package already installed."
else
  echo "Installing autofoam package"
  cd $AUTOFOAM_DIR
  pip install -e .
fi

cd $ROOT_DIR
