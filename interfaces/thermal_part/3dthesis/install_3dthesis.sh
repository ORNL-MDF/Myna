#!/bin/bash

# Check if need to set default directory values
if [ -z "$THESIS_DIR" ]; then
  THESIS_DIR="$(cd ..; pwd)/3DThesis"
fi

# Check if need to set default executable values
if [ -z "$THESIS_EXEC" ]; then
  THESIS_EXEC="3DThesis"
fi

# Clone and build if necessary
ROOT_DIR=$(pwd)
TARGET_COMMIT="36207fc3b626f2a57d475c919e396e89e46990ad"
if [ -d "$THESIS_DIR" ]; then
  echo "$THESIS_DIR already exists."
  cd $THESIS_DIR
  COMMIT=$(git rev-parse HEAD)
  if [ $COMMIT != $TARGET_COMMIT ]; then
    echo "WARNING: Version of target 3DThesis repository"
    echo "does not match recommended value"
    echo "  -- Recommended commit: $TARGET_COMMIT"
    echo "  -- Specified repo commit: $COMMIT"
  fi
else
  echo "Cloning $THESIS_DIR repository"
  cd ..
  git clone https://gitlab.com/JamieStumpORNL/3DThesis.git
  cd 3DThesis
  git checkout $TARGET_COMMIT
fi

# 
if [ -f "$THESIS_DIR/$THESIS_EXEC" ]; then
  echo "$THESIS_DIR/$THESIS_EXEC application already built."
else
  echo "Building 3DThesis"
  cd $THESIS_DIR
  make
  cp ./build/application/$THESIS_EXEC $THESIS_EXEC
fi

cd $ROOT_DIR


