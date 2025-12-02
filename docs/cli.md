---
title: Command Line Interfaces (CLIs)
---

## Peregrine CLI

A command line interface for interacting with the [ORNL-developed Peregrine software](https://www.ornl.gov/technology/90000077)
enables Myna to receive commands to construct and execute simulation pipelines for
a particular set of build, parts, and layers with minimal user input. The CLI is called
via `myna launch_peregrine ...`. Instructions for how to setup and use the Myna tools in
Peregrine are provided in the Peregrine user manual. The documentation here describes
the general functionality of the CLI and how to develop additional functionality.

The main parameter that is used to construct the input file for the specified pipeline
is the `--mode <str>` argument passed to the CLI. This tells Myna which template input
file to use, evaluated as `f"cli/peregrine_launcher/input_{mode}.yaml"`. These templates
have to define the simulation steps to take, though many of the details of each step
are defined by the `peregrine_default_workspace.yaml` file. Additional modes can be
added, but they will only be accessible in Peregrine if corresponding changes are made
within Peregrine.

While this CLI was developed with the intention to interact with Peregrine, it can
generally be used to run cases for specific builds, parts, and layers within a database.
The following examples will run a case using the resources provided with the `myna`
repository.

```bash
# set to the directory where Myna repository was cloned/downloaded
MYNA_PATH="."

# Launch the melt pool geometry simulation
myna launch_peregrine --build "$MYNA_PATH/resources" --parts [P5] --layers [50,51,52] --workspace "$MYNA_PATH/cli/peregrine_launcher/peregrine_default_workspace.yaml" --mode "meltpool_geometry"
```
