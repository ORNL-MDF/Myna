#!/bin/bash
cd ${0%/*} || exit 1  # run from this directory

# source the correct version of ExaCA based
# on {{EXACA_BIN_PATH}} and {{EXACA_EXEC}} specified
# in interface configure script
EXE="{{EXACA_BIN_PATH}}/{{EXACA_EXEC}}"
ANALYSIS="{{EXACA_BIN_PATH}}/grain_analysis"

# Run the ExaCA case
mpiexec -n {{RANKS}} $EXE inputs.json > exaca_run.log 2>&1

# Run the ExaCA analysis script
$ANALYSIS analysis.json ./exaca > exaca_analysis.log 2>&1
