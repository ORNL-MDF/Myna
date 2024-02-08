# Clustering interface examples

## Example 1: Clustering

To configure the example, first update two paths in the input file:

1. The path to the 3DThesis executable (`--exec`) under the `3dthesis` step (line 6)
2. The path to the example Peregrine build `path` (line 35)

To run the example, enter:

```bash
myna_config --input input.yaml
myna_run --input input.yaml
```

The `plot_all_parts.py` script is provide to visualize the results of the clustering.
The resulting output will depend on the training of the voxel and supervoxel models.

**NOTE:** If there is already a clustering modeling in the interface
template folder, it may be overwritten or updated. If you wish to use
a pre-trained clustering model for the voxel and supervoxels clustering
steps, then make sure to use the `--no-training` flag in the clustering
step execute command.

## Example 2: Clustering with RVE selection

Once clusters are generated, the results can be used to determine representative
volume elements (RVEs) from the simulated parts.

To run the example, enter the `myna_config` command followed by the desired `myna_run`
command:

```bash
myna_config --input input_rve.yaml

# If running from scratch:
myna_run --input input_rve.yaml

# If Example #1 has already been run and you want to skip the first steps:
myna_run --input input_rve.yaml --step [rve,additivefoam_cube]

# If Example #1 has already been run and you only want to run the RVE selection:
myna_run --input input_rve.yaml --step rve
```
