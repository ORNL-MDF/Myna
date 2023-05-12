#!/bin/bash

# Check if need to set default directory values
if [ -z "$AUTOTHESIS_DIR" ]; then
  AUTOTHESIS_DIR="$(cd ../..; pwd)/autothesis"
fi

# Clone and build if necessary
ROOT_DIR=$(pwd)
TARGET_COMMIT="81ecf69586f123890f9b438d29ac4ceaf02ef78e"
if [ -d "$AUTOTHESIS_DIR" ]; then
  echo "$AUTOTHESIS_DIR already exists."
  cd $AUTOTHESIS_DIR
  COMMIT=$(git rev-parse HEAD)
  if [ $COMMIT != $TARGET_COMMIT ]; then
    echo "WARNING: Version of target autothesis repository"
    echo "does not match recommended value"
    echo "  -- Recommended commit: $TARGET_COMMIT"
    echo "  -- Specified repo commit: $COMMIT"
  fi
else
  echo "Cloning autothesis repository to $AUTOTHESIS_DIR"
  cd ..
  git clone https://code.ornl.gov/ygk/autothesis.git
  cd autothesis
  git branch -u origin/upgrade upgrade
  git switch upgrade
  git checkout $TARGET_COMMIT
fi

# Install/verify package install
PACKAGE=`conda list | awk -F"[ ',]+" '/^autothesis/{print $1}'`
if [ $PACKAGE = "autothesis" ]; 
then
  echo "autothesis package already installed."
else
  echo "Installing autothesis package"
  cd $AUTOTHESIS_DIR
  pip install -e .
fi

cd $ROOT_DIR
