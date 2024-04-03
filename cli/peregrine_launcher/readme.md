# Peregrine Launcher

This interface is designed to facilitate launching Myna workflows from
Peregrine via the `launch_from_peregrine` script. The modes available to
Peregrine users are defined by the input files following the notation
`input_<mode>.yaml`.

Any variables defined in `config.yaml` can be used in double brackets
as variables in the input file templates. For example, in `input_gv.yaml`
the executable path for 3DThesis is specified by `{{3DTHESIS_EXEC}}`` and
will be replaced by the correct path at runtime.

## Example

To run an example using the resources provided with the `myna` repository, first
open `config.yaml` and set the path to your local installation of 3DThesis. Then use:

```bash
myna_peregrine_launcher /home/cloud/myna/resources [51] [P6] 20e-6 gv
```
