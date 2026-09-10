# Interactive remote 3DThesis example

This example runs a layer-wise 3DThesis solidification workflow through `myna remote`.
It configures the case locally, transfers a portable bundle to an interactive remote
host over SSH, runs it there, and downloads the result snapshot. It does not run
`myna sync`.

Before launching, update the following settings in `input.yaml`:

- Set `myna.compute.host` to an SSH host alias available through your normal SSH
  configuration.
- Set `myna.compute.workdir` to an absolute writable directory on that host.
- Set `myna.compute.command` to the absolute path of the remote environment's
  `myna` executable. The remote host must also have 3DThesis available, either at
  the specified executable path or through a remote workspace set with
  `myna.compute.workspace`. Remove the `myna.compute.workspace` entry if specifying
  the executable on the remote host via the `steps.3dthesis.executable` argument.

Then launch a remote worker. Myna will automatically save its tracker in
the local working directory in `.myna/remote`:

```bash
myna remote --input input.yaml
```

Then inspect and retrieve the run when it completes:

```bash
# Running `myna remote check` or `myna remote update` without the
# --tracker argument will default to the latest tracker
myna remote check --tracker .myna/remote/<uuid>.json
myna remote update --tracker .myna/remote/<uuid>.json
```

Use `myna remote --input input.yaml --wait` to launch and retrieve in one command.
Note that using `--wait` will create a failure if the process is interrupted, for example, due to a network interruption.
Retrieved snapshots are written under `myna_remote/<uuid>/` beside this input file.
For full remote-workflow settings and behavior, see the [CLI documentation](../../../docs/cli.md#interactive-remote-workflow).
