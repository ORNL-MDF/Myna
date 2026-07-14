# Condor layer-wise part solidification example

This case runs the `solidification_part` component with Condor using the included
Peregrine fixture. Ensure the Condor executable is named `condor` and available on
`PATH`, or replace the `executable` value in `input.yaml` with your local executable.

Run the workflow from this directory:

```bash
myna config
myna run
myna sync
```

Configuration creates one Condor JSON case for layer 51. Execution writes Condor's
raw results beneath the case `Data` directory and converts the final `x`, `y`, `G`,
and `V` fields to Myna's `FileGV` CSV format.

Plot the resulting Myna solidification output with:

```bash
uv run python plot_solidification.py
```

That command searches `myna_output/` for `*FileGV.csv` files, rebuilds the `G` and
`V` images with `myna.core.utils.downsample_to_image`, and writes a side-by-side plot
next to each CSV.
