# External code applications

This directory contains applications to wrap models and simulation tools that are
external to the main Myna source code (i.e., not part of the `myna` Python package
functionality).

## Developing new applications

`myna` expects a specific directory and file structure for each application (app):

- Parent directories are named after available application names.
- Child directory names correspond to the component class names defined in
  `src/myna/core/components/component_class_lookup.py`.
- Each available app can contain three Python stage modules that are imported and
  called sequentially with the corresponding arguments from the `myna run` input file:

  1. configure.py <configure_args>
  2. execute.py <execute_args>
  3. postprocess.py <postprocess_args>

- Each stage module should define a function named for the stage (`configure`,
  `execute`, or `postprocess`) or a `main()` function.
- The expectation is that each configure, execute, and postprocess stage will use the
  Python argparse module to parse command line inputs. `myna` temporarily populates
  `sys.argv` for the active stage to preserve command-line parsing behavior.
- Stage code should get workflow state from `MynaApp` attributes rather than directly
  reading `MYNA_*` environment variables.
- If the model has a case template that it will copy from, then the convention is to
  name that directory "template" (this is not strictly necessary).
- Other files can be included in the app directory for documentation or as resources,
  such as a readme file.

There is no technical difference between the three stages on the backend of `myna`.
The split into stages is for organization of tasks into case setup, case execution,
and tasks to be completed after a successful execution.
