# Peregrine Launcher

This interface is designed to facilitate launching Myna workflows from
Peregrine via the `myna launch_peregrine` script. The modes available to
Peregrine users are defined by the input files following the notation
`input_<mode>.yaml` and the specified workspace.

## Example

To run an example using the resources provided with the `myna` repository, run the
following command:

```bash
# set to the directory where Myna repository was cloned
MYNA_PATH="."

# Launch the melt pool geometry simulation
myna launch_peregrine --build "$MYNA_PATH/resources" --parts [P5] --layers [50,51,52] --workspace "$MYNA_PATH/cli/peregrine_launcher/peregrine_default_workspace.yaml" --mode "meltpool_geometry"
```
