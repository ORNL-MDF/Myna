# External code interfaces

This directory contains interfaces to models and codes that are external to
the main Myna source code (i.e., not part of the `myna` Python package
functionality).

# Developing new interfaces

`myna` expects a specific directory and file structure for each interface:
- Parent directories are named after the class names defined in 
[../src/myna/components/component_class_lookup.py].
- Child directory names then correspond to an available interface name
for the parent class
- Each available interface can contain three stages of executables
that will be called sequentially with the corresponding arguments from
the myna_run input file:
  1. configure.py <configure_args>
  2. execute.py <execute_args>
  3. postprocess.py <postprocess_args>
- The expectation is that each configure, execute, and postprocess
script will use the Python argparse module to parse command line inputs
- If the model has a case template that it will copy from, then the
convention is to name that directory "template" (this is
not strictly necessary)
- Other files can be included in the interface directory for documentation or
as resources, such as a readme file

There is no technical difference between the three stages of executables
on the backend of `myna`. The `os.system()` call is the same for each stage.
The split into stages is more for organization of tasks into case setup,
case execution, and tasks to be completed after a (successful) execution, 
which will be useful if implementing a more robust workflow manager in
the future.
