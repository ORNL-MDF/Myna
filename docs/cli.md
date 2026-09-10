---
title: Command Line Interfaces (CLIs)
---

## Interactive remote workflow

`myna remote --input input.yaml` configures and runs a workflow on an interactive
remote host using the user's normal `ssh` and `scp` configuration. It does not submit
to Slurm or another batch scheduler, and it does not run `myna sync`.

Enable it with an optional `myna.compute` dictionary:

```yaml
myna:
  compute:
    host: cloud
    workdir: /home/cloud/myna-workspace
    command: /home/cloud/venv/bin/myna
    workspace: /home/cloud/myna-workspace/apps.yaml  # optional remote-only workspace
    data_location: local  # `local` or `remote`
    download: all         # optional: `all` (default) or `outputs`
```

`host` is an SSH host alias such as one defined in `~/.ssh/config`. `command` must be
the absolute path to the remote virtual environment's `myna` executable; Myna uses its
sibling Python executable and the standard-library `zipfile` module for transfer
archives. Every run receives a unique UUID-named directory below `workdir`.

`myna.compute.workspace` is an optional absolute path to a workspace on the remote
host. It is used only by the remote worker, so the local host need not have that file.
For `data_location: local`, the regular `myna.workspace` and input file options are used;
for `data_location: remote`, the remote workspace file and input file options must be
remote-valid. In both cases, workspace values are defaults: values supplied in the input
file for a workflow step override workspace values, such as the step `executable` and
operation arguments.

With `data_location: local`, Myna configures locally, transfers a portable configured
bundle, runs remotely, then returns the configured bundle and results. With
`data_location: remote`, Myna sends the input as JSON to the remote installation, which
performs both configuration and execution; all build, workspace, and runtime paths in
that input must be valid on the remote host. Every launch starts a detached worker and
prints a local tracker path. Use `--wait` to wait for completion and retrieve results
in one command, or use the tracker later:

```bash
myna remote --input input.yaml
myna remote check --tracker .myna/remote/<uuid>.json
myna remote update --tracker .myna/remote/<uuid>.json
```

The `myna remote check` tool only reports remote job status: `running`, `succeeded`, or `failed`.
The `myna remote update` retrieves a successful archive into `myna_remote/<uuid>/`
beside the input and prints the configured input snapshot path. The original input,
resources, and output tree are not overwritten by subsequent runs, because
each launch is configured from its own snapshot. Omitting `--tracker` uses the newest
unfinished tracker for `--input` (default `input.yaml`).

`download: outputs` retains the remote run directory. The default `download: all`
removes it only after successful local extraction. Failed runs retain the remote
directory and print the remote worker log paths.

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
