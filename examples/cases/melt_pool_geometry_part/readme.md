# 3DThesis melt-pool geometry example

This example uses the `thesis/melt_pool_geometry_part` app. It supports two
3DThesis sampling modes through `steps:3dthesis:configure:sampling-mode`.
This app requires 3DThesis version `4.0.0` or later for both sampling modes.

- `snapshots`
  - Default behavior.
  - Writes `Mode.txt` with the 3DThesis `Snapshots` mode.
  - Produces a time-series of melt-pool geometry samples along the scan path.
  - The exported Myna CSV columns are:
    `x (m)`, `y (m)`, `time (s)`, `length (m)`, `width (m)`, `depth (m)`.

- `xy-grid`
  - Writes `Mode.txt` with the 3DThesis `Solidification` mode and enables
    melt-pool statistics in `Output.txt`.
  - Optional configure flag `steps:3dthesis:configure:mp-stats-interp: true`
    switches the 3DThesis output request to `MP_Stats=0` and
    `MP_Stats_Interp=1`. Note that this feature is experimental and only works
    with a feature that is currently in a feature branch of 3DThesis. Track
    feature merge at [the relevant pull request](https://github.com/ORNL-MDF/3DThesis/pull/40)
    for 3DThesis commit or version dependencies for this option.
  - Produces melt-pool geometry and solidification time at each evaluated grid
    location, which is spatially dense but usually requires more simulation work.
  - The exported Myna CSV columns are the same:
    `x (m)`, `y (m)`, `time (s)`, `length (m)`, `width (m)`, `depth (m)`.
  - In this mode, `time (s)` is the local solidification time (`tSol`), not a
    snapshot time along the path.

The generated case under
`myna_output/P5/51/3dthesis/path_segment_000/` shows the `xy-grid` style 3DThesis
inputs and outputs. Use that folder as a reference if you need to compare the
`Solidification`-mode files against the default snapshot-mode files.
