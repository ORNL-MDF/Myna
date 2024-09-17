#!/bin/bash
cd ${0%/*} || exit 1  # run from this directory

# source the correct version of ExaCA based
# on {{EXACA_BIN_PATH}} and {{EXACA_EXEC}} specified
# in the app's configure.py script
BIN_PATH="{{EXACA_BIN_PATH}}"
EXACA_EXEC="{{EXACA_EXEC}}"
EXE=$BIN_PATH/$EXACA_EXEC

# Run the ExaCA case
mpiexec -n {{RANKS}} $EXE inputs.json > exaca_run.log 2>&1
